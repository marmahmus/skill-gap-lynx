import hashlib
import logging
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from modules import config, interview

logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)


class AppFlowTests(unittest.TestCase):
    def test_interview_retry_report_and_reset(self):
        with patch.object(config, "GROQ_API_KEY", "test"), patch.object(config, "youtube_enabled", return_value=False):
            app = AppTest.from_file("app.py", default_timeout=15).run()
            self.assertFalse(app.exception)
            app.session_state.results = {"candidate_name": "Demo", "match_percentage": 50,
                "matching_skills": ["Python"], "missing_skills": ["SQL"], "roadmap": [], "feedback": "Demo"}
            app.session_state.cv_text = "Python developer"
            app.session_state.jd_text = "Python SQL role"
            app.session_state.voice_on = False
            app.run()
            with patch.object(interview, "generate_questions", return_value=["Q1", "Q2", "Q3", "Q4"]):
                next(b for b in app.button if b.label == "Start Interview").click().run()
            self.assertFalse(app.exception)
            app.text_area[-1].set_value("My saved answer").run()
            with patch.object(interview, "evaluate_answer", return_value={"error": "outage", "score": None}):
                next(b for b in app.button if b.label == "Submit answer").click().run()
            self.assertEqual(app.session_state.iv_index, 0)
            self.assertEqual(app.session_state["answer_0"], "My saved answer")
            for _ in range(4):
                with patch.object(interview, "evaluate_answer", return_value={"score": 8, "language": "English", "strengths": "Good", "improvements": "Detail"}), patch.object(interview, "generate_final_report", return_value={"error": "outage", "overall_score": 80, "recommendation": "Hire", "summary": "Demo", "strengths": [], "improvements": []}):
                    next(b for b in app.button if b.label == "Submit answer").click().run()
                self.assertFalse(app.exception)
            self.assertTrue(app.session_state.iv_done)
            with patch.object(interview, "generate_final_report", return_value={"overall_score": 80, "recommendation": "Hire", "summary": "Recovered", "strengths": [], "improvements": []}):
                next(b for b in app.button if b.label == "Retry report feedback").click().run()
            self.assertIsNone(app.session_state.report_error)
            next(b for b in app.button if b.label == "Start Over").click().run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.session_state.results)

    def test_input_change_invalidates_old_results(self):
        with patch.object(config, "GROQ_API_KEY", "test"), patch.object(config, "youtube_enabled", return_value=False):
            app = AppTest.from_file("app.py").run()
            app.session_state.results = {"candidate_name": "Old"}
            app.session_state.input_signature = hashlib.sha256(b"old CV\0old JD").hexdigest()
            app.text_area[0].set_value("Updated JD").run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.session_state.results)


if __name__ == "__main__":
    unittest.main()
