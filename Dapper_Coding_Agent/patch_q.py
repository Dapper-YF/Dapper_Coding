#!/usr/bin/env python3
# Patch Phase 14 quiz into learning_agent.py

with open('/opt/Dapper_Coding_Agent/learning_agent.py', 'r', encoding='utf-8') as f:
    content2 = f.read()

old2 = (
    '        self.dialogue_manager.add_user_message(user_id, channel, user_message)\n'
    '        \n'  # 8 spaces blank line
    '        # 2. 获取对话上下文\n'
    '        context = self.dialogue_manager.build_context(user_id, channel, limit=10)\n'
    '        \n'  # 8 spaces blank line
    '        # 2.5 Check if this is a learning context query (dialogue teaching)\n'
    '        if self._is_learning_query(user_id, user_message):'
)

new2 = (
    '        self.dialogue_manager.add_user_message(user_id, channel, user_message)\n'
    '        \n'
    '        # 2. 优先检测：有没有未答的课后题\n'
    '        try:\n'
    '            from quiz_engine import get_pending_quiz, grade_quiz, update_mastery_score\n'
    '            pending = get_pending_quiz(user_id)\n'
    '            if pending:\n'
    '                result = grade_quiz(pending["id"], user_message)\n'
    '                skipped = result.get("skipped", False)\n'
    '                is_correct = result["is_correct"]\n'
    '\n'
    '                if skipped:\n'
    '                    reply = "✅ 已跳过这道题～ 有问题随时问我！"\n'
    '                    try:\n'
    '                        from learning_scout import get_latest_generated_lesson\n'
    '                        lesson = get_latest_generated_lesson(user_id)\n'
    '                        if lesson:\n'
    '                            topic = lesson.get("title", "")[:30]\n'
    '                            update_mastery_score(user_id, topic, -0.1, lesson.get("id"))\n'
    '                    except:\n'
    '                        pass\n'
    '                elif is_correct:\n'
    '                    reply = "✅ 回答正确！太棒了！\\n\\n继续加油，有问题随时问我～"\n'
    '                    try:\n'
    '                        from learning_scout import get_latest_generated_lesson\n'
    '                        lesson = get_latest_generated_lesson(user_id)\n'
    '                        if lesson:\n'
    '                            topic = lesson.get("title", "")[:30]\n'
    '                            update_mastery_score(user_id, topic, 0.2, lesson.get("id"))\n'
    '                    except:\n'
    '                        pass\n'
    '                else:\n'
    '                    reply = ("❌ 不对哦，正确答案是 **{}**\\n\\n"\n'
    '                             "别担心，这正好是学习的好机会！\\n可以再看看课程内容，或者直接问我～"\n'
    '                            ).format(result["correct_answer"])\n'
    '                    try:\n'
    '                        from learning_scout import get_latest_generated_lesson\n'
    '                        lesson = get_latest_generated_lesson(user_id)\n'
    '                        if lesson:\n'
    '                            topic = lesson.get("title", "")[:30]\n'
    '                            update_mastery_score(user_id, topic, -0.3, lesson.get("id"))\n'
    '                    except:\n'
    '                        pass\n'
    '\n'
    '                self.dialogue_manager.add_assistant_message(user_id, channel, reply)\n'
    '                return reply\n'
    '        except Exception as exc:\n'
    '            logging.warning("quiz check failed (non-blocking): %s", exc)\n'
    '\n'
    '        # 2. 获取对话上下文\n'
    '        context = self.dialogue_manager.build_context(user_id, channel, limit=10)\n'
    '        \n'
    '        # 2.5 Check if this is a learning context query (dialogue teaching)\n'
    '        if self._is_learning_query(user_id, user_message):'
)

if old2 in content2:
    content2 = content2.replace(old2, new2)
    with open('/opt/Dapper_Coding_Agent/learning_agent.py', 'w', encoding='utf-8') as f:
        f.write(content2)
    print('PATCH 2 OK: learning_agent.py')
else:
    print('ERROR: PATCH 2 failed - pattern not found')
