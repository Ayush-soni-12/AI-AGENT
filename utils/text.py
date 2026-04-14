import tiktoken


def get_tokenizer(model:str):
    try:
        encoding = tiktoken.encoding_for_model(model)
        return encoding.encode
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
        return encoding.encode


def count_tokens(model:str , text:str) -> int:
    tokenizer = get_tokenizer(model)
    if tokenizer:
        return len(tokenizer(text))

    return estimate_token(text)


def estimate_token(text:str) -> int:
    return max(1,len(text)//4)