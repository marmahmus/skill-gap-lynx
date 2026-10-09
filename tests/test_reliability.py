import unittest
from unittest.mock import patch, Mock

from modules import groq_analyzer as ga, interview as iv, groq_client as gc, youtube


class ReliabilityTests(unittest.TestCase):
    def analyze(self, response, cv="Python developer"):
        with patch.object(ga, "chat_json", return_value=response):
            return ga.analyze_profile(cv, "Python and SQL required")

    def test_empty_and_invalid_flags_rejected(self):
        for response in ({}, {"required_skills": [{"skill": "Python", "present": "false"}]}):
            self.assertIn("error", self.analyze(response))

    def test_no_substring_or_aspiration_promotions(self):
        matching, missing = ga._reconcile([], ["Go", "R", "SQL"], "Django developer. Want to learn SQL.")
        self.assertEqual(matching, [])
        self.assertEqual(len(missing), 3)
        self.assertFalse(ga._mentioned_in_text("go", "Django"))
        self.assertFalse(ga._mentioned_in_text("c", "C++"))

    def test_negative_claim_demoted(self):
        self.assertEqual(ga._reconcile(["SQL"], [], "No SQL experience"), ([], ["SQL"]))

    def test_aliases_deduped_and_roadmap_consistent(self):
        response = {"candidate_name": 123, "feedback": [], "required_skills": [
            {"skill": "React.js", "present": True}, {"skill": "React JS", "present": True},
            {"skill": "SQL", "present": False}], "roadmap": [
            {"skill": "React", "action": "Learn React"}]}
        result = self.analyze(response)
        self.assertEqual(result["match_percentage"], 50)
        self.assertEqual(result["candidate_name"], "Candidate")
        self.assertEqual([row["skill"] for row in result["roadmap"]], ["SQL"])

    def test_failed_evaluation_not_scored(self):
        with patch.object(iv, "chat_json", side_effect=gc.GroqError("outage")):
            evaluation = iv.evaluate_answer("Q", "Answer", "JD")
        self.assertIsNone(evaluation["score"])
        self.assertIn("error", evaluation)
        self.assertEqual(iv._avg_score([{"eval": {"score": 8}}, {"eval": evaluation}]), 80)

    def test_invalid_evaluation_rejected(self):
        for score in (None, "NaN", True, -1, 11, {}):
            with patch.object(iv, "chat_json", return_value={"score": score}):
                self.assertIn("error", iv.evaluate_answer("Q", "Answer", "JD"))

    def test_question_shape_and_language(self):
        with patch.object(iv, "chat_json", return_value={"questions": "bad"}):
            with self.assertRaises(gc.GroqError):
                iv.generate_questions("CV", "JD", [], [])
        with patch.object(iv, "chat_json", return_value={"questions": ["پہلا سوال", "دوسرا سوال", "تیسرا سوال", "چوتھا سوال"]}) as call:
            self.assertEqual(len(iv.generate_questions("CV", "JD", [], [], language="Urdu")), 4)
            self.assertIn("Urdu", call.call_args.args[0][1]["content"])

    def test_report_score_is_answer_average(self):
        with patch.object(iv, "chat_json", return_value={"overall_score": 99, "recommendation": 123, "summary": [], "strengths": "bad"}):
            report = iv.generate_final_report([{"question": "Q", "eval": {"score": 6}}], 90, "JD")
        self.assertEqual(report["overall_score"], 60)
        self.assertEqual(report["recommendation"], "Maybe")
        self.assertEqual(report["strengths"], [])

    def test_http_errors_and_non_object_json(self):
        for status, data in [(401, {}), (503, {}), (200, []), (200, {"error": "bad"})]:
            response = Mock(status_code=status)
            response.json.return_value = data
            with self.assertRaises(gc.GroqError):
                gc._safe_response_json(response)

    def test_retry_transient_http(self):
        first, second = Mock(status_code=503, headers={}), Mock(status_code=200)
        second.json.return_value = {"ok": True}
        with patch.object(gc.requests, "post", side_effect=[first, second]), patch.object(gc.time, "sleep"):
            self.assertEqual(gc._post_with_retry("url", {}, {}), {"ok": True})

    def test_video_empty_vs_failure(self):
        response = Mock(status_code=200)
        response.json.return_value = {"items": []}
        with patch.object(youtube.requests, "get", return_value=response):
            self.assertIsNone(youtube._lookup("SQL"))
        response.status_code = 403
        with patch.object(youtube.requests, "get", return_value=response):
            with self.assertRaises(youtube.VideoError):
                youtube._lookup("SQL")


if __name__ == "__main__":
    unittest.main()
