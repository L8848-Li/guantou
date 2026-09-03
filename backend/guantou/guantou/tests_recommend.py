from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from user.models import UserFollow, UserInfo

from .models import (
    Can,
    CanComment,
    CanLike,
    Dialect,
    DialectCircle,
    Nameplate,
    NameplateSupport,
)


class RecommendedFeedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        DialectCircle.objects.all().delete()
        Dialect.objects.all().delete()
        self.root = Dialect.objects.create(name="闽语", code="闽")
        self.child = Dialect.objects.create(
            name="莆仙话", code="莆仙", parent=self.root
        )
        self.other = Dialect.objects.create(name="客家话", code="客家")

        self.author = User.objects.create_user(username="speaker", password="pw")
        UserInfo.objects.create(
            user=self.author, nickname="录音者", primary_dialect=self.child
        )
        self.other_author = User.objects.create_user(username="other", password="pw")
        UserInfo.objects.create(
            user=self.other_author, nickname="他人", primary_dialect=self.other
        )
        self.user = User.objects.create_user(username="listener", password="pw")
        UserInfo.objects.create(user=self.user, nickname="听友")

    def make_can(self, dialect, concept, recorder=None, **extra):
        values = {
            "audio_url": f"https://example.com/{concept}.mp3",
            "recorder": recorder or self.author,
            "submitted_dialect": dialect,
            "concept_text": concept,
            "visibility": True,
        }
        values.update(extra)
        return Can.objects.create(**values)

    def like(self, can, user):
        return CanLike.objects.create(can=can, user=user)

    def comment(self, can, user):
        return CanComment.objects.create(can=can, author=user, content="好")

    def add_active_nameplate(self, can):
        return Nameplate.objects.create(
            can=can,
            text_content="样",
            status=Nameplate.Status.ACTIVE,
            source={"type": "creator"},
            creator=self.author,
        )

    def support(self, nameplate, user):
        return NameplateSupport.objects.create(nameplate=nameplate, user=user)

    def recommended(self, user=None, **params):
        if user is not None:
            self.client.force_authenticate(user)
        else:
            self.client.force_authenticate(user=None)
        return self.client.get("/cans/", {"feed": "recommended", **params})

    def test_guest_ordered_by_hotness(self):
        hot = self.make_can(self.child, "热门", views=10)
        for i in range(3):
            self.like(hot, User.objects.create_user(username=f"l{i}", password="pw"))
        cold = self.make_can(self.other, "冷门", views=5)

        response = self.recommended()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], hot.id)
        self.assertEqual(response.data["results"][0]["recommend_reasons"], ["hot"])

    def test_time_decay_prefers_fresher_can(self):
        fresh = self.make_can(self.child, "新", views=10)
        stale = self.make_can(self.other, "旧", views=10)
        Can.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(days=30)
        )

        response = self.recommended()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], fresh.id)

    def test_same_dialect_boost_and_reason(self):
        self.user.user_info.primary_dialect = self.child
        self.user.user_info.save(update_fields=["primary_dialect"])

        local = self.make_can(self.child, "乡音", views=0)
        popular = self.make_can(self.other, "爆款", views=50)

        response = self.recommended(self.user)

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertLess(ids.index(local.id), ids.index(popular.id))
        reasons = {
            item["id"]: item["recommend_reasons"] for item in response.data["results"]
        }
        self.assertIn("same_dialect", reasons[local.id])
        self.assertEqual(reasons[popular.id], ["hot"])

    def test_following_boost_and_reason(self):
        UserFollow.objects.create(follower=self.user, followed=self.author)
        from_author = self.make_can(self.other, "关注", views=0, recorder=self.author)
        popular = self.make_can(
            self.other, "爆款", views=50, recorder=self.other_author
        )

        response = self.recommended(self.user)

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertLess(ids.index(from_author.id), ids.index(popular.id))
        reasons = {
            item["id"]: item["recommend_reasons"] for item in response.data["results"]
        }
        self.assertIn("following", reasons[from_author.id])

    def test_supports_contribute_to_hotness(self):
        supported = self.make_can(self.child, "背书", views=0)
        self.support(self.add_active_nameplate(supported), self.author)
        plain = self.make_can(self.other, "无背书", views=1)

        response = self.recommended()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["id"], supported.id)

    def test_recommend_reasons_empty_outside_feed(self):
        self.make_can(self.child, "普通", views=1)
        response = self.client.get("/cans/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["recommend_reasons"], [])

    def test_pagination_is_stable(self):
        created = [self.make_can(self.child, f"罐{i}", views=i) for i in range(30)]
        seen = []
        params = {"feed": "recommended", "page_size": 7}
        for page in (1, 2, 3, 4, 5):
            response = self.recommended(page=page, **params)
            self.assertEqual(response.status_code, 200)
            seen.extend(item["id"] for item in response.data["results"])
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(set(seen), {can.id for can in created})

    def test_empty_behavior_falls_back_stably(self):
        a = self.make_can(self.child, "甲")
        b = self.make_can(self.other, "乙")

        response = self.recommended()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]], [b.id, a.id]
        )
        self.assertEqual(response.data["results"][0]["recommend_reasons"], ["hot"])
