class AppError(Exception):
    """입력 데이터 없이 공개용 오류 코드와 메시지만 보관한다."""

    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status
