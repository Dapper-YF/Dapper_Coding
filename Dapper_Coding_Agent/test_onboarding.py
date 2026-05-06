# -*- coding: utf-8 -*-
"""
Learning Scout Onboarding API 测试脚本
覆盖所有 onboarding API + 双轨认证

用法:
    python test_onboarding.py [--base-url http://localhost:8000]
"""

import sys
import json
import os
import uuid
import argparse


class TestRunner:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        self.admin_token = os.getenv("API_TOKEN", "dev_token_mvp")
        self.user_token = None
        self.user_id = None
        self.device_id = f"test_device_{uuid.uuid4().hex[:12]}"

    def _headers(self, token=None):
        t = token or self.admin_token
        return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}

    def _req(self, method, path, json_data=None, token=None, expected_status=200):
        import requests
        url = f"{self.base_url}{path}"
        h = self._headers(token)
        try:
            if method == "GET":
                resp = requests.get(url, headers=h, timeout=10)
            elif method == "POST":
                resp = requests.post(url, headers=h, json=json_data, timeout=10)
            elif method == "PUT":
                resp = requests.put(url, headers=h, json=json_data, timeout=10)
            else:
                raise ValueError(f"Unknown method: {method}")
        except requests.exceptions.ConnectionError:
            return None, f"连接失败: {url} 无法访问，请确认服务已启动"

        if resp.status_code != expected_status:
            return resp, f"HTTP {resp.status_code} (expected {expected_status}): {resp.text[:200]}"
        try:
            return resp, resp.json()
        except Exception:
            return resp, resp.text

    def test(self, name, method, path, json_data=None, token=None, expected_status=200, validators=None):
        resp, body = self._req(method, path, json_data, token, expected_status)
        if isinstance(body, str) and body.startswith("连接失败"):
            print(f"  FAIL  {name}: {body}")
            self.failed += 1
            return False
        if isinstance(body, str) and resp is not None and resp.status_code != expected_status:
            print(f"  FAIL  {name}: {body}")
            self.failed += 1
            return False
        if resp is not None and resp.status_code != expected_status:
            print(f"  FAIL  {name}: HTTP {resp.status_code}: {body}")
            self.failed += 1
            return False

        if validators:
            for v in validators:
                ok, msg = v(body)
                if not ok:
                    print(f"  FAIL  {name}: {msg}")
                    self.failed += 1
                    return False

        print(f"  PASS  {name}")
        self.passed += 1
        return True

    def run(self):
        print("=" * 60)
        print("Learning Scout Onboarding API 测试")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)

        # ---- Phase 1: Auth ----
        print("\n[Phase 1] Auth API")

        # 1.1 Register
        self.test(
            "POST /api/auth/register — 新用户注册",
            "POST", "/api/auth/register",
            json_data={"device_id": self.device_id},
            validators=[
                lambda b: (b.get("user_id", "").startswith("dev_"), f"user_id 格式错误: {b.get('user_id')}"),
                lambda b: (len(b.get("token", "")) > 20, "token 为空或太短"),
                lambda b: (b.get("new_user") == True, f"new_user 应为 True: {b.get('new_user')}"),
                lambda b: (b.get("onboarding_complete") == False, "onboarding_complete 应为 False"),
            ]
        )

        # 1.2 Re-register same device
        self.test(
            "POST /api/auth/register — 重复设备注册（返回已有账户）",
            "POST", "/api/auth/register",
            json_data={"device_id": self.device_id},
            validators=[
                lambda b: (b.get("new_user") == False, f"new_user 应为 False: {b.get('new_user')}"),
                lambda b: (b.get("onboarding_complete") == False, "onboarding_complete 应为 False"),
            ]
        )

        # 1.3 Login
        self.test(
            "POST /api/auth/login — 正常登录",
            "POST", "/api/auth/login",
            json_data={"device_id": self.device_id},
            validators=[
                lambda b: (len(b.get("token", "")) > 20, "token 为空或太短"),
                lambda b: (b.get("user_id", "").startswith("dev_"), "user_id 格式错误"),
            ]
        )

        # 1.4 Login with wrong device_id
        self.test(
            "POST /api/auth/login — 未注册设备登录",
            "POST", "/api/auth/login",
            json_data={"device_id": "nonexistent_device_999"},
            expected_status=404,
        )

        # 1.5 Register without device_id
        self.test(
            "POST /api/auth/register — 缺少 device_id",
            "POST", "/api/auth/register",
            json_data={},
            expected_status=400,
        )

        # 1.6 Verify token (admin)
        self.test(
            "GET /api/auth/verify — admin token 验证",
            "GET", "/api/auth/verify",
            token=self.admin_token,
            validators=[
                lambda b: (b.get("valid") == True, f"valid 应为 True: {b.get('valid')}"),
                lambda b: (b.get("user_id") == "admin", f"user_id 应为 admin: {b.get('user_id')}"),
            ]
        )

        # 1.7 Verify invalid token
        self.test(
            "GET /api/auth/verify — 无效 token",
            "GET", "/api/auth/verify",
            token="invalid_token_12345",
            expected_status=401,
        )

        # Register a user and save the JWT for later tests
        resp, body = self._req("POST", "/api/auth/register",
                               json_data={"device_id": self.device_id})
        if body and isinstance(body, dict):
            self.user_token = body.get("token")
            self.user_id = body.get("user_id")
            print(f"  [INFO] user_id={self.user_id} token={self.user_token[:30]}...")

        # ---- Phase 2: Onboarding Tree ----
        print("\n[Phase 2] Onboarding Tree API")

        # 2.1 Get tree
        def validate_tree(body):
            tree = body.get("tree")
            if not tree or not isinstance(tree, list) or len(tree) == 0:
                return False, f"tree 为空或格式错误: {body}"
            root = tree[0]
            if root.get("id") != "q_identity":
                return False, f"根节点应为 q_identity: {root.get('id')}"
            # 验证有分支
            options = root.get("options", [])
            if len(options) < 2:
                return False, f"q_identity options 不足: {len(options)}"

            # 验证 CS branch 存在（通过 children 链）
            cs_found = False
            ai_found = False
            def check_node(node):
                nonlocal cs_found, ai_found
                if node.get("id") == "q_cs_branch":
                    cs_found = True
                if node.get("id") == "q_cs_ai_detail":
                    ai_found = True
                for opt in node.get("options", []):
                    for child in opt.get("children", []):
                        check_node(child)
            check_node(root)
            if not cs_found:
                return False, "问卷树缺少 q_cs_branch 节点"
            if not ai_found:
                return False, "问卷树缺少 q_cs_ai_detail 追问分支"
            return True, ""

        self.test(
            "GET /api/onboarding/tree — 获取完整问卷树",
            "GET", "/api/onboarding/tree",
            token=self.user_token,
            validators=[validate_tree],
        )

        # 2.2 Tree with admin token
        self.test(
            "GET /api/onboarding/tree — admin token 获取问卷树",
            "GET", "/api/onboarding/tree",
            token=self.admin_token,
            validators=[validate_tree],
        )

        # ---- Phase 2: Onboarding Complete ----
        print("\n[Phase 2] Onboarding Complete API")

        # 场景1: 学生在校生 → CS → AI → NLP + DL
        cs_answers = [
            {"question_id": "q_identity", "answer": "student"},
            {"question_id": "q_major", "answer": "cs"},
            # q_interest skipped (student + cs_major goes directly to q_cs_branch)
            {"question_id": "q_cs_branch", "answer": ["cs_ai", "cs_web"]},
            {"question_id": "q_cs_ai_detail", "answer": ["cs_ai_nlp", "cs_ai_dl", "cs_ai_unsure"]},
            {"question_id": "q_cs_web_detail", "answer": ["cs_web_full"]},
            {"question_id": "q_cs_level", "answer": "level_intermediate"},
            {"question_id": "q_goal", "answer": ["goal_career", "goal_hobby"]},
        ]

        def validate_cs_profile(body):
            profile = body.get("profile", {})
            if profile.get("identity") != "student":
                return False, f"identity 应为 student: {profile.get('identity')}"
            if profile.get("identity_detail") != "cs":
                return False, f"identity_detail 应为 cs: {profile.get('identity_detail')}"

            interests_detail = profile.get("interests_detail", {})
            ai_detail = interests_detail.get("artificial_intelligence", [])
            if "nlp" not in ai_detail:
                return False, f"AI detail 应包含 nlp: {ai_detail}"
            if "deep_learning" not in ai_detail:
                return False, f"AI detail 应包含 deep_learning: {ai_detail}"

            unsure = profile.get("unsure_topics", [])
            if "cs_ai_unsure" not in unsure:
                return False, f"unsure_topics 应包含 cs_ai_unsure: {unsure}"

            skill_levels = profile.get("skill_levels", {})
            if skill_levels.get("nlp") != "intermediate":
                return False, f"nlp skill 应为 intermediate: {skill_levels.get('nlp')}"

            goals = profile.get("learning_goals", [])
            if "career" not in goals or "hobby" not in goals:
                return False, f"learning_goals 应包含 career 和 hobby: {goals}"

            if body.get("status") != "ok":
                return False, f"status 应为 ok: {body.get('status')}"
            return True, ""

        self.test(
            "POST /api/onboarding/complete — CS学生→AI(NLP+DL)",
            "POST", "/api/onboarding/complete",
            json_data={"answers": cs_answers},
            token=self.user_token,
            validators=[validate_cs_profile],
        )

        # 场景2: 物理爱好者
        phys_answers = [
            {"question_id": "q_identity", "answer": "hobbyist"},
            {"question_id": "q_interest", "answer": ["physics", "math"]},
            {"question_id": "q_physics_branch", "answer": ["physics_quantum", "physics_unsure"]},
            {"question_id": "q_math_branch", "answer": ["math_linalg", "math_prob"]},
            {"question_id": "q_physics_level", "answer": "level_beginner"},
            {"question_id": "q_math_level", "answer": "level_intermediate"},
            {"question_id": "q_goal", "answer": ["goal_hobby"]},
        ]

        def validate_phys_profile(body):
            profile = body.get("profile", {})
            interests_detail = profile.get("interests_detail", {})
            if "quantum_physics" not in interests_detail:
                return False, f"应包含 quantum_physics: {interests_detail}"
            unsure = profile.get("unsure_topics", [])
            if "physics_unsure" not in unsure:
                return False, f"unsure 应包含 physics_unsure: {unsure}"
            skill_levels = profile.get("skill_levels", {})
            if skill_levels.get("quantum_physics") != "beginner":
                return False, f"quantum_physics skill 应为 beginner: {skill_levels}"
            return True, ""

        # 注册第二个用户
        device2 = f"test_phys_{uuid.uuid4().hex[:8]}"
        resp2, body2 = self._req("POST", "/api/auth/register",
                                 json_data={"device_id": device2})
        phys_token = body2.get("token") if body2 and isinstance(body2, dict) else None

        self.test(
            "POST /api/onboarding/complete — 物理爱好者→量子物理",
            "POST", "/api/onboarding/complete",
            json_data={"answers": phys_answers},
            token=phys_token,
            validators=[validate_phys_profile],
        )

        # 场景3: Empty answers
        self.test(
            "POST /api/onboarding/complete — 空答案",
            "POST", "/api/onboarding/complete",
            json_data={"answers": []},
            token=self.user_token,
            expected_status=400,
        )

        # ---- Phase 3: Profile API ----
        print("\n[Phase 3] Profile API")

        def validate_get_profile(body):
            profile = body.get("profile")
            if profile is None:
                return False, "profile 不应为 None"
            if not profile.get("onboarding_complete"):
                return False, "onboarding_complete 应为 True"
            if profile.get("identity") != "student":
                return False, f"identity 应为 student: {profile.get('identity')}"
            return True, ""

        self.test(
            "GET /api/user/profile — 获取用户人设",
            "GET", "/api/user/profile",
            token=self.user_token,
            validators=[validate_get_profile],
        )

        # Profile with admin (no profile)
        self.test(
            "GET /api/user/profile — admin 获取 profile",
            "GET", "/api/user/profile",
            token=self.admin_token,
            validators=[
                lambda b: (b.get("profile") is None, "admin profile 应为 None"),
            ]
        )

        # Update profile — LA 修正 unsure_topics
        self.test(
            "PUT /api/user/profile — Learning Agent 修正 unsure_topics",
            "PUT", "/api/user/profile",
            json_data={"unsure_topics": ["cs_mobile_unsure", "cs_ai_unsure"]},
            token=self.user_token,
            validators=[
                lambda b: (b.get("status") == "ok", f"status 应为 ok: {b.get('status')}"),
                lambda b: ("cs_mobile_unsure" in b.get("updated_topics", []),
                          f"应包含 cs_mobile_unsure: {b.get('updated_topics')}"),
                # 原有的 cs_ai_unsure 应保留（merge）
                lambda b: ("cs_ai_unsure" in b.get("updated_topics", []),
                          f"应包含原有 cs_ai_unsure: {b.get('updated_topics')}"),
            ]
        )

        # Update profile — missing field
        self.test(
            "PUT /api/user/profile — 缺少 unsure_topics",
            "PUT", "/api/user/profile",
            json_data={},
            token=self.user_token,
            expected_status=400,
        )

        # ---- Phase 4: Edge Cases ----
        print("\n[Phase 4] Edge Cases")

        # Invalid JWT
        self.test(
            "GET /api/onboarding/tree — 无效 JWT",
            "GET", "/api/onboarding/tree",
            token="eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiZmFrZSJ9.fakesig",
            expected_status=401,
        )

        # Expired token (synthetic)
        self.test(
            "POST /api/auth/login — 不存在的 device_id",
            "POST", "/api/auth/login",
            json_data={"device_id": "completely_fake_device_000"},
            expected_status=404,
        )

        # Login with device_id missing
        self.test(
            "POST /api/auth/login — 缺少 device_id",
            "POST", "/api/auth/login",
            json_data={},
            expected_status=400,
        )

        # Admin token accessing all APIs
        self.test(
            "GET /api/user/stats — admin token（已升级双轨）",
            "GET", "/api/user/stats",
            token=self.admin_token,
        )

        self.test(
            "GET /api/conversations — admin token",
            "GET", "/api/conversations",
            token=self.admin_token,
        )

        # ---- Summary ----
        print("\n" + "=" * 60)
        total = self.passed + self.failed
        print(f"测试结果: {self.passed}/{total} 通过", end="")
        if self.failed > 0:
            print(f", {self.failed} 失败")
        else:
            print(" ✓ 全部通过")
        print("=" * 60)
        return self.failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Learning Scout Onboarding API 测试")
    parser.add_argument("--base-url", default="http://localhost:8000",
                       help="API server base URL (default: http://localhost:8000)")
    args = parser.parse_args()

    runner = TestRunner(base_url=args.base_url)
    success = runner.run()
    sys.exit(0 if success else 1)
