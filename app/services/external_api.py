# Backward compatibility: eski importlar buzilmasligi uchun yangi student clientni shu yerdan ham eksport qilamiz.
from .student.external_student_api import PDPStudentAPIClient, PDPStudentAPIError

__all__ = ["PDPStudentAPIClient", "PDPStudentAPIError"]
