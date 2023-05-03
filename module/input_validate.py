# input() 이용하여 입력받을 때 입력값 검증, 입력과 관련된 코드를 모듈화 함.

def input_until_get_data(default_prompt) -> str:
    """
    입력값이 있을때까지 반복하여 입력받고, 입력받은 값을 리턴
    참고로 입력값이 있다는건 공백을 제외한 어떤 값이라도 입력받은 상태를 의미함.
    :param default_prompt: 입력값이 없을때 출력할 문구
    """
    query = ""
    while not query.strip():
        query = input(default_prompt)
    return query


def input_until_correct_download_range(default_prompt, error_prompt) -> str:
    """
    입력값이 "숫자" 또는 "숫자-숫자" 만 입력할때까지 반복하여 입력받고, 입력받은 값을 리턴
    :param default_prompt: 입력을 받을때 출력할 문구
    :param error_prompt: 입력값이 잘못되었을때 출력할 문구
    """

    dialog = input(default_prompt).strip()

    while (True):
        if dialog.isdigit() or (dialog.find('-') != -1 and dialog.split('-')[0].isdigit() and dialog.split('-')[1].isdigit()):
            break
        else:
            dialog = input(error_prompt).strip()

    return dialog
