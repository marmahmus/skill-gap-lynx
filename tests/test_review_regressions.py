import io
import unittest
import zipfile
from unittest.mock import Mock, patch

from modules import groq_client as gc, groq_analyzer as ga, interview as iv
from modules.resume_reader import read_resume


class ReviewRegressionTests(unittest.TestCase):
    def test_not_only_is_not_negation(self):
        self.assertEqual(ga._reconcile(["Python"], [], "Not only Python but also SQL"), (["Python"], []))

    def test_network_timeout_retries(self):
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True}
        with patch.object(gc.requests, "post", side_effect=[gc.requests.Timeout(), response]) as post, patch.object(gc.time, "sleep"):
            self.assertEqual(gc._post_with_retry("url", {}, {}), {"ok": True})
            self.assertEqual(post.call_count, 2)

    def test_wrong_script_questions_rejected(self):
        with patch.object(iv, "chat_json", return_value={"questions": ["a", "b", "c", "d"]}):
            with self.assertRaises(gc.GroqError):
                iv.generate_questions("CV", "JD", [], [], language="Urdu")

    def test_word_tables_and_corrupt_input(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Candidate</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Python</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        self.assertEqual(read_resume(stream.getvalue(), "CV.docx"), "Candidate\nPython")
        with self.assertRaises(ValueError):
            read_resume(b"invalid", "CV.docx")

    def test_urdu_transcription_parameter_and_script(self):
        response = Mock(status_code=200)
        response.json.return_value = {"text": "میرا جواب"}
        with patch.object(gc.config, "GROQ_API_KEY", "test"), patch.object(gc.requests, "post", return_value=response) as post:
            self.assertEqual(gc.transcribe(b"audio", language="Urdu"), "میرا جواب")
            self.assertEqual(post.call_args.kwargs["data"]["language"], "ur")
            response.json.return_value = {"text": "मेरा जवाब"}
            with self.assertRaises(gc.GroqError):
                gc.transcribe(b"audio", language="Urdu")
