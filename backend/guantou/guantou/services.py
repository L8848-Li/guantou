from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from utils.exceptions.types.bad_request import BadRequestException
from utils.exceptions.types.forbidden import ForbiddenException

from .models import Can, Flavor, FlavorPackage, FlavorVariant, Nameplate, Package

DEFAULT_SEARCH_LIMIT = 8
MAX_SEARCH_LIMIT = 20

# 合法状态转换表：{action: {from_status: to_status}}
CAN_TRANSITIONS = {
    "submit": {"pending": "tentative"},
    "verify": {"tentative": "verified"},
    "dispute": {"tentative": "disputed"},
    "reject": {
        "pending": "rejected",
        "disputed": "rejected",
    },
    "restore": {"rejected": "pending"},
}

# 需要 staff/verifier 权限的操作
STAFF_ONLY_ACTIONS = {"verify", "reject"}


def clean_text(value):
    return str(value or "").strip()


def result_limit(value):
    try:
        return min(max(int(value), 1), MAX_SEARCH_LIMIT)
    except (TypeError, ValueError):
        return DEFAULT_SEARCH_LIMIT


def visible_cans_for_user(user):
    queryset = Can.objects.select_related(
        "recorder", "dialect", "flavor_variant", "verifier"
    ).prefetch_related("nameplates")
    if user and user.is_authenticated and user.is_staff:
        return queryset
    if user and user.is_authenticated:
        return queryset.filter(Q(visibility=True) | Q(recorder=user))
    return queryset.filter(visibility=True)


def search_flavors(keyword, limit):
    return (
        Flavor.objects.prefetch_related("packages", "variants")
        .filter(
            Q(name__icontains=keyword)
            | Q(definition__icontains=keyword)
            | Q(mandarin__icontains=keyword)
            | Q(packages__text__icontains=keyword)
        )
        .distinct()[:limit]
    )


def search_packages(keyword, limit):
    return (
        Package.objects.prefetch_related("flavors")
        .filter(text__icontains=keyword)
        .distinct()[:limit]
    )


def search_cans(keyword, user, limit):
    return (
        visible_cans_for_user(user)
        .filter(
            Q(concept_text__icontains=keyword)
            | Q(nameplates__text_content__icontains=keyword)
            | Q(nameplates__definition__icontains=keyword)
        )
        .distinct()[:limit]
    )


def aggregate_search(keyword, user=None, limit=DEFAULT_SEARCH_LIMIT):
    clean_keyword = clean_text(keyword)
    if not clean_keyword:
        return {
            "keyword": "",
            "flavors": [],
            "packages": [],
            "cans": [],
        }

    normalized_limit = result_limit(limit)
    return {
        "keyword": clean_keyword,
        "flavors": search_flavors(clean_keyword, normalized_limit),
        "packages": search_packages(clean_keyword, normalized_limit),
        "cans": search_cans(clean_keyword, user, normalized_limit),
    }


def get_or_create_package(label):
    text = clean_text(label.get("text_content"))
    if not text:
        return None
    package_type = label.get("package_type") or Package.PackageType.UNCERTAIN
    package, _ = Package.objects.get_or_create(
        text=text,
        package_type=package_type,
        defaults={"metadata": {}},
    )
    return package


def get_or_create_submission_flavor(can, label, user, package):
    flavor_id = label.get("flavor")
    if flavor_id:
        return Flavor.objects.filter(id=flavor_id).first()

    if not package:
        return None

    definition = clean_text(label.get("definition")) or can.concept_text or package.text
    flavor = Flavor.objects.create(
        name=definition,
        definition=definition,
        mandarin=[can.concept_text] if can.concept_text else [],
        created_by=user if user and user.is_authenticated else None,
    )
    FlavorPackage.objects.get_or_create(flavor=flavor, package=package)
    return flavor


def create_initial_nameplate(can, label, user):
    text_content = clean_text(label.get("text_content"))
    if not text_content:
        return None

    package = get_or_create_package(label)
    flavor = get_or_create_submission_flavor(can, label, user, package)
    nameplate = Nameplate.objects.create(
        can=can,
        flavor=flavor,
        package=package,
        creator=user,
        text_content=text_content,
        definition=clean_text(label.get("definition")) or can.concept_text,
        evidence_level=label.get("evidence_level") or Nameplate.EvidenceLevel.MEMORY,
        source_citation=clean_text(label.get("source_citation")),
    )
    nameplate.promote_to_primary()
    if can.status == Can.Status.UNLABELED:
        can.status = Can.Status.PENDING
        can.save(update_fields=["status", "updated_at"])
    return nameplate


def create_flavor_variant_for_can(can_data, flavor, user):
    return FlavorVariant.objects.create(
        flavor=flavor,
        dialect=can_data.get("dialect"),
        audio_url=can_data.get("audio_url", ""),
        audio_source=FlavorVariant.AudioSource.USER,
        created_by=user if user and user.is_authenticated else None,
    )


@transaction.atomic
def create_can_submission(*, user, can_data, initial_nameplate=None, flavor=None):
    data = dict(can_data)
    if flavor:
        data["flavor_variant"] = create_flavor_variant_for_can(data, flavor, user)
        data["concept_text"] = data.get("concept_text") or flavor.name
    data["recorder"] = user

    can = Can.objects.create(**data)
    if initial_nameplate:
        create_initial_nameplate(can, initial_nameplate, user)
    return can


@transaction.atomic
def transition_can(*, can_id: int, user, action: str, reason: str) -> Can:
    """事务内锁定 Can 行，执行状态转换并追加审计日志。

    并发语义：先提交者成功，后提交者重新读取到已变更的状态，
    因「当前状态不在合法来源集合」抛出 BadRequestException，而不是覆盖前者。
    注意：SQLite 不支持 SELECT ... FOR UPDATE，select_for_update 会静默降级为无锁。
    """
    if action not in CAN_TRANSITIONS:
        raise BadRequestException(f"未知操作: {action}")

    can = Can.objects.select_for_update().get(pk=can_id)

    # 权限检查：verify/reject 仅 is_staff 或该 Can 的 verifier 可执行
    if action in STAFF_ONLY_ACTIONS:
        if not (user.is_staff or can.verifier == user):
            raise ForbiddenException("您没有权限执行此操作")
    else:
        # submit/dispute/restore 允许创建者或 staff 操作
        if not (user.is_staff or can.recorder == user):
            raise ForbiddenException("您没有权限执行此操作")

    # 检查状态转换是否合法
    allowed_transitions = CAN_TRANSITIONS[action]
    current_status = can.status
    if current_status not in allowed_transitions:
        raise BadRequestException(
            f"不允许从 {current_status} 转换到 {action} 的目标状态"
        )

    new_status = allowed_transitions[current_status]

    # 记录转换日志；整体赋值确保 JSONField 脏标记触发更新
    log_entry = {
        "from": current_status,
        "to": new_status,
        "by": user.id,
        "at": timezone.now().isoformat(),
        "reason": reason,
    }
    can.transition_log = list(can.transition_log) + [log_entry]
    can.status = new_status

    # verify 时设置 verifier
    if action == "verify":
        can.verifier = user

    can.save(update_fields=["status", "transition_log", "verifier", "updated_at"])
    return can
