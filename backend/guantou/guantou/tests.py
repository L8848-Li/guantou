from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    Can,
    Dialect,
    Flavor,
    FlavorVariant,
    Nameplate,
    NameplateSupport,
    Package,
)
from user.tokens import generate_token


def bearer(user):
    return f"Bearer {generate_token(user)}"


class GuantouApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="collector", password="pw")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.root = Dialect.objects.create(name="莆仙方言", code="puxian")
        self.child = Dialect.objects.create(
            name="游洋话",
            code="puxian-youyang",
            parent=self.root,
            county="莆田",
            town="游洋",
        )
        self.package = Package.objects.create(
            text="行", package_type=Package.PackageType.ORTHODOX
        )
        self.flavor = Flavor.objects.create(
            name="行走", definition="走路", created_by=self.user
        )
        self.flavor.packages.add(self.package)

    def test_create_can_and_nameplate(self):
        can_res = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/audio.mp3",
                "dialect": self.child.id,
                "concept_text": "走路",
                "county": "莆田",
                "town": "游洋",
            },
            format="json",
        )
        self.assertEqual(can_res.status_code, 201)
        can_id = can_res.data["id"]
        plate_res = self.client.post(
            f"/cans/{can_id}/nameplates/",
            {
                "flavor": self.flavor.id,
                "package": self.package.id,
                "text_content": "行",
                "definition": "走路",
            },
            format="json",
        )
        self.assertEqual(plate_res.status_code, 201)
        can = Can.objects.get(id=can_id)
        self.assertEqual(can.recorder, self.user)
        self.assertEqual(can.status, Can.Status.PENDING)
        self.assertTrue(can.primary_nameplate.is_primary)

    def test_authenticated_user_can_add_nameplate_to_public_can(self):
        other_user = User.objects.create_user(username="labeler", password="pw")
        can = Can.objects.create(
            audio_url="https://example.com/audio.mp3",
            recorder=self.user,
            dialect=self.child,
            concept_text="走路",
            visibility=True,
        )
        client = APIClient()
        client.force_authenticate(user=other_user)

        response = client.post(
            f"/cans/{can.id}/nameplates/",
            {
                "flavor": self.flavor.id,
                "package": self.package.id,
                "text_content": "趁行",
                "definition": "走路",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        plate = Nameplate.objects.get(id=response.data["id"])
        self.assertEqual(plate.creator, other_user)
        self.assertEqual(plate.can, can)

    def test_create_can_without_candidate_nameplate(self):
        response = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/plain.mp3",
                "dialect": self.child.id,
                "concept_text": "knee",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        can = Can.objects.get(id=response.data["id"])
        self.assertEqual(can.recorder, self.user)
        self.assertEqual(can.status, Can.Status.UNLABELED)
        self.assertEqual(can.nameplates.count(), 0)

    def test_create_can_with_initial_nameplate_creates_related_objects(self):
        response = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/knee.mp3",
                "dialect": self.child.id,
                "concept_text": "knee",
                "initial_nameplate": {
                    "text_content": "khnee",
                    "definition": "kneecap",
                    "package_type": Package.PackageType.PHONETIC,
                    "evidence_level": Nameplate.EvidenceLevel.COMMUNITY,
                    "source_citation": "elder",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        can = Can.objects.get(id=response.data["id"])
        plate = can.primary_nameplate
        self.assertIsNotNone(plate)
        self.assertEqual(can.status, Can.Status.PENDING)
        self.assertEqual(plate.text_content, "khnee")
        self.assertEqual(plate.package.package_type, Package.PackageType.PHONETIC)
        self.assertEqual(plate.flavor.definition, "kneecap")
        self.assertEqual(plate.creator, self.user)

    def test_create_can_for_existing_flavor_creates_variant(self):
        response = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/flavor.mp3",
                "dialect": self.child.id,
                "flavor": self.flavor.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        can = Can.objects.get(id=response.data["id"])
        self.assertEqual(can.flavor_variant.flavor, self.flavor)
        self.assertEqual(can.flavor_variant.audio_url, can.audio_url)
        self.assertEqual(can.concept_text, self.flavor.name)

    def test_validation_errors_use_unified_shape(self):
        response = self.client.post(
            "/cans/",
            {
                "dialect": self.child.id,
                "concept_text": "knee",
            },
            format="json",
            HTTP_X_REQUEST_ID="test-request-id",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIn("msg", response.data)
        self.assertIn("message", response.data)
        self.assertIn("details", response.data)
        self.assertEqual(response.data["request_id"], "test-request-id")
        self.assertEqual(response["X-Request-ID"], "test-request-id")

    def test_vote_promotes_strongest_nameplate(self):
        can = Can.objects.create(
            audio_url="https://example.com/audio.mp3",
            recorder=self.user,
            dialect=self.child,
            concept_text="走路",
        )
        weak = Nameplate.objects.create(
            can=can,
            creator=self.user,
            text_content="行",
            flavor=self.flavor,
            package=self.package,
            is_primary=True,
        )
        strong = Nameplate.objects.create(
            can=can,
            creator=self.user,
            text_content="趁行",
            flavor=self.flavor,
            package=self.package,
            weight=2,
        )
        vote_res = self.client.post(
            f"/nameplates/{strong.id}/vote/", {"delta": 1}, format="json"
        )
        self.assertEqual(vote_res.status_code, 200)
        weak.refresh_from_db()
        strong.refresh_from_db()
        self.assertFalse(weak.is_primary)
        self.assertTrue(strong.is_primary)
        self.assertEqual(strong.weight, 3)
        self.assertTrue(
            NameplateSupport.objects.filter(nameplate=strong, user=self.user).exists()
        )
        self.assertTrue(vote_res.data["supported_by_current_user"])

    def test_repeated_vote_by_same_user_does_not_increment_weight(self):
        can = Can.objects.create(
            audio_url="https://example.com/audio.mp3",
            recorder=self.user,
            dialect=self.child,
            concept_text="走路",
        )
        plate = Nameplate.objects.create(
            can=can,
            creator=self.user,
            text_content="行",
            flavor=self.flavor,
            package=self.package,
        )

        first_res = self.client.post(
            f"/nameplates/{plate.id}/vote/", {"delta": 1}, format="json"
        )
        second_res = self.client.post(
            f"/nameplates/{plate.id}/vote/", {"delta": 1}, format="json"
        )

        self.assertEqual(first_res.status_code, 200)
        self.assertEqual(second_res.status_code, 200)
        plate.refresh_from_db()
        self.assertEqual(plate.weight, 1)
        self.assertEqual(NameplateSupport.objects.filter(nameplate=plate).count(), 1)

    def test_different_users_can_support_same_nameplate_once_each(self):
        other_user = User.objects.create_user(username="supporter", password="pw")
        can = Can.objects.create(
            audio_url="https://example.com/audio.mp3",
            recorder=self.user,
            dialect=self.child,
            concept_text="走路",
        )
        plate = Nameplate.objects.create(
            can=can,
            creator=self.user,
            text_content="行",
            flavor=self.flavor,
            package=self.package,
        )

        self.client.post(f"/nameplates/{plate.id}/vote/", {"delta": 1}, format="json")
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        other_client.post(f"/nameplates/{plate.id}/vote/", {"delta": 1}, format="json")

        plate.refresh_from_db()
        self.assertEqual(plate.weight, 2)
        self.assertEqual(NameplateSupport.objects.filter(nameplate=plate).count(), 2)

    def test_parent_dialect_filter_includes_children(self):
        can = Can.objects.create(
            audio_url="https://example.com/audio.mp3",
            recorder=self.user,
            dialect=self.child,
            visibility=True,
        )
        response = self.client.get("/cans/", {"dialect": self.root.id})
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(can.id, ids)

    def test_flavor_package_and_nameplate_model_national_lookup(self):
        moon = Flavor.objects.create(
            name="月亮",
            definition="地球的天然卫星；夜晚可见的天体",
            mandarin=["月亮"],
            created_by=self.user,
        )
        yueliang = Package.objects.create(
            text="月亮", package_type=Package.PackageType.ORTHODOX
        )
        yueguang = Package.objects.create(
            text="月光", package_type=Package.PackageType.POPULAR
        )
        moon.packages.add(yueliang, yueguang)
        can = Can.objects.create(
            audio_url="https://example.com/moon.mp3",
            recorder=self.user,
            dialect=self.child,
            concept_text="月亮",
            visibility=True,
        )
        plate = Nameplate.objects.create(
            can=can,
            creator=self.user,
            flavor=moon,
            package=yueguang,
            text_content="月光",
            definition="月亮",
            is_primary=True,
        )

        self.assertEqual(plate.flavor, moon)
        self.assertEqual(plate.package, yueguang)
        self.assertCountEqual(
            list(moon.packages.values_list("text", flat=True)), ["月亮", "月光"]
        )
        response = self.client.get("/cans/", {"flavor": moon.id})
        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertIn(can.id, ids)

    def test_package_detail_includes_related_flavors(self):
        response = self.client.get(f"/packages/{self.package.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["text"], "行")
        self.assertEqual(len(response.data["flavors"]), 1)
        self.assertEqual(response.data["flavors"][0]["name"], "行走")


class BearerAuthenticationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="collector", password="pw")
        self.dialect = Dialect.objects.create(name="Puxian", code="puxian")

    def test_bearer_token_authenticates_drf_write_request(self):
        client = APIClient()
        response = client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/audio.mp3",
                "dialect": self.dialect.id,
                "concept_text": "moon",
            },
            format="json",
            HTTP_AUTHORIZATION=bearer(self.user),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Can.objects.get(id=response.data["id"]).recorder, self.user)

    def test_legacy_token_header_no_longer_authenticates_drf_write_request(self):
        client = APIClient()
        response = client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/audio.mp3",
                "dialect": self.dialect.id,
                "concept_text": "moon",
            },
            format="json",
            HTTP_TOKEN=generate_token(self.user),
        )

        self.assertEqual(response.status_code, 401)


class CanTransitionTests(TestCase):
    """罐头状态转换端点测试"""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.other_user = User.objects.create_user(username="other", password="pw")
        self.staff_user = User.objects.create_user(
            username="staff", password="pw", is_staff=True
        )
        self.dialect = Dialect.objects.create(name="莆仙方言", code="puxian")
        self.can = Can.objects.create(
            audio_url="https://example.com/audio.mp3",
            recorder=self.owner,
            dialect=self.dialect,
            status=Can.Status.PENDING,
            visibility=True,
        )

    def _client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_staff_verify_legal_transition(self):
        """合法转换：staff 用户执行 submit，pending→tentative，返回 200 + 完整 Can JSON"""
        client = self._client_for(self.staff_user)
        res = client.post(
            f"/cans/{self.can.id}/transition/",
            {"action": "submit", "reason": "社区确认"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "tentative")
        self.assertEqual(res.data["id"], self.can.id)
        # 验证 transition_log 记录
        self.can.refresh_from_db()
        self.assertEqual(len(self.can.transition_log), 1)
        log = self.can.transition_log[0]
        self.assertEqual(log["from"], "pending")
        self.assertEqual(log["to"], "tentative")
        self.assertEqual(log["by"], self.staff_user.id)
        self.assertEqual(log["reason"], "社区确认")
        self.assertIn("at", log)

    def test_staff_verify_after_submit(self):
        """合法转换：staff 用户执行 verify，tentative→verified"""
        self.can.status = Can.Status.TENTATIVE
        self.can.save(update_fields=["status"])
        client = self._client_for(self.staff_user)
        res = client.post(
            f"/cans/{self.can.id}/transition/",
            {"action": "verify", "reason": ""},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "verified")
        self.can.refresh_from_db()
        self.assertEqual(self.can.verifier, self.staff_user)

    def test_non_staff_verify_returns_403(self):
        """权限拒绝：非 staff 用户调 verify 返回 403"""
        self.can.status = Can.Status.TENTATIVE
        self.can.save(update_fields=["status"])
        client = self._client_for(self.other_user)
        res = client.post(
            f"/cans/{self.can.id}/transition/",
            {"action": "verify"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_assigned_verifier_can_verify(self):
        """被分配为 verifier 的非 staff 用户可以执行 verify"""
        self.can.status = Can.Status.TENTATIVE
        self.can.visibility = False
        self.can.verifier = self.other_user
        self.can.save(update_fields=["status", "visibility", "verifier"])
        client = self._client_for(self.other_user)
        res = client.post(
            f"/cans/{self.can.id}/transition/",
            {"action": "verify", "reason": "assigned review"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "verified")
        self.can.refresh_from_db()
        self.assertEqual(self.can.verifier, self.other_user)

    def test_illegal_transition_from_unlabeled(self):
        """非法转换：从 unlabeled 直接调 verify 返回 400"""
        self.can.status = Can.Status.UNLABELED
        self.can.save(update_fields=["status"])
        client = self._client_for(self.staff_user)
        res = client.post(
            f"/cans/{self.can.id}/transition/",
            {"action": "verify"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertIn("不允许从", body["msg"])
        self.assertEqual(body["code"], "bad_request")

    def test_illegal_transition_submit_from_unlabeled(self):
        """非法转换：从 unlabeled 调 submit 返回 400（必须先经过 pending）"""
        self.can.status = Can.Status.UNLABELED
        self.can.save(update_fields=["status"])
        client = self._client_for(self.owner)
        res = client.post(
            f"/cans/{self.can.id}/transition/",
            {"action": "submit"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_transition_log_accumulates(self):
        """transition_log 正确记录多次操作"""
        client = self._client_for(self.staff_user)
        # pending -> tentative
        client.post(
            f"/cans/{self.can.id}/transition/",
            {"action": "submit", "reason": "first"},
            format="json",
        )
        # tentative -> verified
        client.post(
            f"/cans/{self.can.id}/transition/",
            {"action": "verify", "reason": "second"},
            format="json",
        )
        self.can.refresh_from_db()
        self.assertEqual(len(self.can.transition_log), 2)
        self.assertEqual(self.can.transition_log[0]["from"], "pending")
        self.assertEqual(self.can.transition_log[0]["to"], "tentative")
        self.assertEqual(self.can.transition_log[1]["from"], "tentative")
        self.assertEqual(self.can.transition_log[1]["to"], "verified")


class IsOwnerOrAdminPermissionTests(TestCase):
    """对象级权限测试：PUT/DELETE 仅允许创建者或 staff"""

    def setUp(self):
        self.user_a = User.objects.create_user(username="userA", password="pw")
        self.user_b = User.objects.create_user(username="userB", password="pw")
        self.staff_user = User.objects.create_user(
            username="admin", password="pw", is_staff=True
        )
        self.dialect = Dialect.objects.create(name="莆仙方言", code="puxian")
        self.can = Can.objects.create(
            audio_url="https://example.com/audio.mp3",
            recorder=self.user_a,
            dialect=self.dialect,
            visibility=True,
        )

    def _client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_owner_can_put(self):
        """用户 A 自己调 PUT 修改返回 200"""
        client = self._client_for(self.user_a)
        res = client.patch(
            f"/cans/{self.can.id}/",
            {"concept_text": "新概念"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.can.refresh_from_db()
        self.assertEqual(self.can.concept_text, "新概念")

    def test_non_owner_put_returns_403(self):
        """用户 A 创建的 Can，用户 B（非 staff）调 PUT 修改返回 403"""
        client = self._client_for(self.user_b)
        res = client.patch(
            f"/cans/{self.can.id}/",
            {"concept_text": "恶意修改"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_staff_can_put(self):
        """staff 用户可以修改任何资源"""
        client = self._client_for(self.staff_user)
        res = client.patch(
            f"/cans/{self.can.id}/",
            {"concept_text": "管理员修改"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    def test_non_owner_delete_returns_403(self):
        """非创建者非 staff 删除返回 403"""
        client = self._client_for(self.user_b)
        res = client.delete(f"/cans/{self.can.id}/")
        self.assertEqual(res.status_code, 403)

    def test_owner_can_delete(self):
        """创建者可以删除自己的资源"""
        client = self._client_for(self.user_a)
        res = client.delete(f"/cans/{self.can.id}/")
        self.assertEqual(res.status_code, 204)

    def test_get_not_restricted(self):
        """任何登录用户都可以 GET"""
        client = self._client_for(self.user_b)
        res = client.get(f"/cans/{self.can.id}/")
        self.assertEqual(res.status_code, 200)


class CanViewCountTests(TestCase):
    """罐头浏览量原子计数测试"""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.visitor = User.objects.create_user(username="visitor", password="pw")
        self.dialect = Dialect.objects.create(name="莆仙方言", code="puxian")
        self.can = Can.objects.create(
            audio_url="https://example.com/audio.mp3",
            recorder=self.owner,
            dialect=self.dialect,
            visibility=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.visitor)

    def test_retrieve_increments_views_atomically(self):
        """连续两次 retrieve 后 views == 初始值 + 2，且响应中为最新值"""
        initial = self.can.views
        for expected in (initial + 1, initial + 2):
            res = self.client.get(f"/cans/{self.can.id}/")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.data["views"], expected)
        self.can.refresh_from_db()
        self.assertEqual(self.can.views, initial + 2)

    def test_retrieve_does_not_touch_updated_at(self):
        """浏览只更新 views，不刷新 updated_at"""
        before = Can.objects.values_list("updated_at", flat=True).get(pk=self.can.pk)
        res = self.client.get(f"/cans/{self.can.id}/")
        self.assertEqual(res.status_code, 200)
        after = Can.objects.values_list("updated_at", flat=True).get(pk=self.can.pk)
        self.assertEqual(before, after)


class CanSubmissionContractTests(TestCase):
    """POST /cans/ 装罐提交端到端 API 契约测试（#97）

    通过 DRF APIClient 走真实路由，以现行 CanSerializer 输出为契约基准：
    断言字段名与类型，防止前后端联调前的契约漂移。
    """

    # POST /cans/ 成功响应必须包含的契约字段
    CAN_CONTRACT_FIELDS = (
        "id",
        "audio_url",
        "dialect",
        "concept_text",
        "status",
        "duration_ms",
        "nameplates",
        "primary_nameplate",
        "flavor_variant",
    )
    CAN_STATUSES = {choice[0] for choice in Can.Status.choices}

    def setUp(self):
        self.user = User.objects.create_user(username="canner", password="pw")
        self.dialect = Dialect.objects.create(name="莆仙方言", code="puxian")
        self.flavor = Flavor.objects.create(
            name="行走", definition="走路", created_by=self.user
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _assert_can_contract(self, data):
        """断言响应包含契约字段且类型正确"""
        for field in self.CAN_CONTRACT_FIELDS:
            self.assertIn(field, data)
        self.assertIsInstance(data["id"], int)
        self.assertIsInstance(data["audio_url"], str)
        self.assertIsInstance(data["concept_text"], str)
        self.assertIsInstance(data["duration_ms"], int)
        self.assertIsInstance(data["nameplates"], list)
        self.assertIn(data["status"], self.CAN_STATUSES)
        self.assertTrue(data["dialect"] is None or isinstance(data["dialect"], int))
        self.assertTrue(
            data["flavor_variant"] is None or isinstance(data["flavor_variant"], int)
        )
        self.assertTrue(
            data["primary_nameplate"] is None
            or isinstance(data["primary_nameplate"], dict)
        )

    def _assert_unified_error_shape(self, response, code):
        """断言错误响应符合统一 shape：msg/message/code/details/request_id"""
        for field in ("msg", "message", "code", "details", "request_id"):
            self.assertIn(field, response.data)
        self.assertEqual(response.data["code"], code)
        self.assertEqual(response.data["request_id"], "contract-request-id")
        self.assertEqual(response["X-Request-ID"], "contract-request-id")

    def test_submit_free_canning_without_nameplate(self):
        """自由装罐（无铭牌）→ 201，status == unlabeled"""
        response = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/free.mp3",
                "dialect": self.dialect.id,
                "concept_text": "膝盖",
                "duration_ms": 1500,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self._assert_can_contract(response.data)
        self.assertEqual(response.data["status"], Can.Status.UNLABELED)
        self.assertEqual(response.data["duration_ms"], 1500)
        self.assertEqual(response.data["nameplates"], [])
        self.assertIsNone(response.data["primary_nameplate"])
        self.assertIsNone(response.data["flavor_variant"])
        self.assertEqual(response.data["recorder"]["id"], self.user.id)

    def test_submit_free_canning_with_initial_nameplate(self):
        """带 initial_nameplate 自由装罐 → 201，铭牌提升为主铭牌，unlabeled→pending 自动推进"""
        response = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/labeled.mp3",
                "dialect": self.dialect.id,
                "concept_text": "走路",
                "initial_nameplate": {
                    "text_content": "行",
                    "definition": "走路",
                    "package_type": Package.PackageType.ORTHODOX,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self._assert_can_contract(response.data)
        self.assertEqual(response.data["status"], Can.Status.PENDING)
        self.assertEqual(len(response.data["nameplates"]), 1)
        primary = response.data["primary_nameplate"]
        self.assertIsNotNone(primary)
        self.assertTrue(primary["is_primary"])
        self.assertEqual(primary["text_content"], "行")
        # 铭牌连带创建 Package/Flavor 并落库
        can = Can.objects.get(id=response.data["id"])
        plate = can.nameplates.get()
        self.assertTrue(plate.is_primary)
        self.assertEqual(plate.creator, self.user)
        self.assertIsNotNone(plate.package)
        self.assertIsNotNone(plate.flavor)

    def test_submit_repeated_nameplate_text_does_not_duplicate_package(self):
        """重复提交相同写法文本 → Package 按 get_or_create 语义复用，不重复创建"""
        payload = {
            "audio_url": "https://example.com/dup.mp3",
            "dialect": self.dialect.id,
            "concept_text": "走路",
            "initial_nameplate": {
                "text_content": "行",
                "definition": "走路",
                "package_type": Package.PackageType.ORTHODOX,
            },
        }
        first = self.client.post("/cans/", payload, format="json")
        second = self.client.post("/cans/", payload, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(
            Package.objects.filter(
                text="行", package_type=Package.PackageType.ORTHODOX
            ).count(),
            1,
        )

    def test_submit_repeated_nameplate_text_creates_new_flavor_each_time(self):
        """现状固化：初始铭牌每次提交都新建 Flavor，未复用既有义项。

        与 #97 期望的 get_or_create 复用语义存在偏差，如需改为复用请单独开 issue，
        修复后本用例应改为断言 Flavor 计数不变。
        """
        payload = {
            "audio_url": "https://example.com/dup.mp3",
            "dialect": self.dialect.id,
            "concept_text": "走路",
            "initial_nameplate": {
                "text_content": "行",
                "definition": "走路",
                "package_type": Package.PackageType.ORTHODOX,
            },
        }
        first = self.client.post("/cans/", payload, format="json")
        second = self.client.post("/cans/", payload, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        first_flavor = first.data["nameplates"][0]["flavor"]
        second_flavor = second.data["nameplates"][0]["flavor"]
        self.assertIsNotNone(first_flavor)
        self.assertIsNotNone(second_flavor)
        self.assertNotEqual(first_flavor, second_flavor)

    def test_submit_supplement_recording_for_existing_flavor(self):
        """补录音传 flavor id → 201，flavor_variant 自动创建，concept_text 回填义项名称"""
        response = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/variant.mp3",
                "dialect": self.dialect.id,
                "flavor": self.flavor.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self._assert_can_contract(response.data)
        self.assertIsNotNone(response.data["flavor_variant"])
        self.assertEqual(response.data["concept_text"], self.flavor.name)
        variant = FlavorVariant.objects.get(id=response.data["flavor_variant"])
        self.assertEqual(variant.flavor, self.flavor)
        self.assertEqual(variant.dialect, self.dialect)
        self.assertEqual(variant.audio_url, "https://example.com/variant.mp3")
        self.assertEqual(variant.audio_source, FlavorVariant.AudioSource.USER)
        self.assertEqual(variant.created_by, self.user)

    def test_submit_with_initial_nameplate_and_flavor_combined(self):
        """initial_nameplate 与 flavor 同时传入 → 两者均生效（现行实现无歧义）"""
        response = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/combined.mp3",
                "dialect": self.dialect.id,
                "flavor": self.flavor.id,
                "initial_nameplate": {
                    "text_content": "行",
                    "definition": "走路",
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self._assert_can_contract(response.data)
        # flavor 路径：变体创建且 concept_text 回填
        self.assertIsNotNone(response.data["flavor_variant"])
        self.assertEqual(response.data["concept_text"], self.flavor.name)
        # 初始铭牌路径：铭牌创建并提升，状态推进到 pending
        self.assertEqual(response.data["status"], Can.Status.PENDING)
        self.assertEqual(len(response.data["nameplates"]), 1)
        self.assertTrue(response.data["primary_nameplate"]["is_primary"])

    def test_submit_without_authentication_returns_401(self):
        """未登录提交 → 401，错误响应符合统一 shape"""
        anon = APIClient()
        response = anon.post(
            "/cans/",
            {
                "audio_url": "https://example.com/anon.mp3",
                "concept_text": "膝盖",
            },
            format="json",
            HTTP_X_REQUEST_ID="contract-request-id",
        )
        self.assertEqual(response.status_code, 401)
        self._assert_unified_error_shape(response, "not_authenticated")

    def test_submit_missing_audio_url_returns_400(self):
        """缺少必填 audio_url → 400，details 指明字段，错误 shape 统一"""
        response = self.client.post(
            "/cans/",
            {"concept_text": "膝盖"},
            format="json",
            HTTP_X_REQUEST_ID="contract-request-id",
        )
        self.assertEqual(response.status_code, 400)
        self._assert_unified_error_shape(response, "validation_error")
        self.assertIn("audio_url", response.data["details"])

    def test_submit_invalid_dialect_returns_400(self):
        """非法 dialect 主键 → 400，错误 shape 统一"""
        response = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/bad-dialect.mp3",
                "dialect": 999999,
            },
            format="json",
            HTTP_X_REQUEST_ID="contract-request-id",
        )
        self.assertEqual(response.status_code, 400)
        self._assert_unified_error_shape(response, "validation_error")
        self.assertIn("dialect", response.data["details"])

    def test_submit_without_concept_text_and_flavor_current_behavior(self):
        """现状固化：concept_text 与 flavor 均缺失时返回 201 无标罐头。

        #97 口径原期望 400；如契约需收紧为必填其一，请单独开 issue，
        修复后本用例应改为断言 400。
        """
        response = self.client.post(
            "/cans/",
            {
                "audio_url": "https://example.com/bare.mp3",
                "dialect": self.dialect.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self._assert_can_contract(response.data)
        self.assertEqual(response.data["status"], Can.Status.UNLABELED)
        self.assertEqual(response.data["concept_text"], "")
