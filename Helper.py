def _strip_json_fence(text):
    """移除模型可能返回的 ```json / ``` 包裹。
    Remove optional markdown code fences like ```json / ``` from model output.
    """
    if not isinstance(text, str):
        return text
    t = text.strip()
    if t.startswith("```") and t.endswith("```"):
        lines = t.splitlines()
        if len(lines) >= 3:
            t = "\n".join(lines[1:-1]).strip()
    return t

def _decode_unicode_if_escaped(text):
    """仅在包含 \\u 转义时尝试解码，避免破坏正常中文。
    Decode only when unicode escapes exist to avoid corrupting normal text.
    """
    if not isinstance(text, str):
        return text
    if "\\u" not in text:
        return text
    try:
        return bytes(text, "utf-8").decode("unicode_escape")
    except Exception:
        return text
    

import json


def transform_profile_to_json(profile_msg:str) :
    """将模型返回的人设 JSON 字符串解析为 Python 字典。
    Parse persona JSON string from model output into a Python dictionary.

    参数:
        profile_msg: str，模型输出的 JSON 文本。
    Arguments:
        profile_msg: str, JSON text returned by the model.

    返回:
        dict | None: 解析成功返回字典，失败返回 None。
    Returns:
        dict | None: Parsed dictionary on success, otherwise None.
    """
    import json

    try:
        cleaned = _strip_json_fence(profile_msg)
        profile_json = json.loads(cleaned)

        # 处理 character 可能被二次转义（例如 "\\u6211..."）的情况。
        # Handle cases where character is escaped twice (for example "\\u6211...").
        if isinstance(profile_json, dict) and "character" in profile_json:
            char_val = profile_json.get("character")
            if isinstance(char_val, str):
            # 若是被再次 JSON 包裹的字符串，先尝试 json.loads。
            # If wrapped as a JSON string again, try json.loads first.
                try:
                    if char_val.startswith('"') and char_val.endswith('"'):
                        char_val = json.loads(char_val)
                except Exception:
                    pass
                profile_json["character"] = _decode_unicode_if_escaped(char_val)

        return profile_json
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}")
        return None
