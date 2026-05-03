import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from http import HTTPStatus
from typing import Any
import supabase
import Helper 
from dashscope import Application
from dashscope import Generation
import random
supabase_client = supabase.create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# 画像生成机器人提示词
# Profile bot prompt



prompt_p = """只输出合法标准 JSON，无任何多余文字、解释、序号、注释。
输出结构严格如下：
{
  "character": "一段详细、完整的用户人设初稿，包含性格、住宿偏好、生活习惯、诉求，3～5句话，自然真实（必须是 内地人/香港人/澳门人/台湾人）",
  "profile": {
    "gender": "Male" / "Female",
    "identity": "New local undergraduate" / "Continuing local undergraduate" / "New non-local undergraduate" / "Continuing non-local undergraduate",
    "priorities": ["Quiet","Convenience","Price","Social","Sea View","Facilities"],
    "room_types": ["Single Room","Double Room","Triple Room"],
    "budget_range": "HK$ 14,000 - 20,000" / "HK$ 20,000 - 26,000" / "HK$ 26,000 - 38,000" / "HK$ 38,000+",
    "additional_info": "更细致的补充信息(简单一句话,不要交代个人身份性格等信息，只针对住宿需求的补充)，如果没有可以填 None"
  }
}

规则：
1. character 内容详细、立体，像真实学生，不要太短。
2. profile 内容与 character 保持一致。
3. 严格 JSON 格式，双引号，无语法错误。
4. 只输出 JSON，不输出任何其他内容。"""

## 问题生成机器人提示词
## Question bot prompt

language = "一定要简体中文，不要粤语用词"

prompt_q_compare = f"""

你是“测评问题生成器”，只模拟学生提问，绝对不回答问题。

规则：
1. 语言为 {language}。
2. 可使用宿舍别名/混写，如“宿舍x”“hall x”“xxx宿舍”。
3. 只输出纯问题，**绝对不要加任何个人想法、需求铺垫、理由说明**。
4. 不要出现“如果我想…”“我要…”“我比较在意…”这类自我描述。
5. 可包含价格、日期、数量等简单数字需求，不夹带已知数据。

6. （最重要，优先完成这条）. ** 问题必须包含多宿舍对比/宿舍环境/住宿体验感受 **
7. 禁止括号、抄写资料、书面化、模板化。
8. 询问同一个宿舍时，问题中省略掉宿舍名称
9. 只输出一条问题，禁止一次输出多个问题
10. 严格仅限**单一独立问题**，禁止复合问句、禁止用逗号拆分拼接两个提问、禁止一句话内含两个不同疑问点
11. 若上一轮回答明确说明知识库没有相关内容，立即放弃当前提问领域，更换全新独立领域出题，不继续追问同主题相关问题

【随机风格规则】
- 有概率不用“那、请问、有没有”开头
- 有概率省略句末问号
- 有概率不用标点
- 句式自然随机，禁止全部都是“那xxx嗎？”
- 有概率省略掉宿舍名称，直接问需求
- 有概率打乱语序

【绝对禁止】
- 禁止回答、禁止引用知识库
- 禁止解释、总结、说明
- 禁止出现“根据资料…”“答案是…”
- 禁止输出个人想法、需求前提、主观描述
- 禁止主动提供信息，只提问
- 禁止输出多条问题，只输出一条问题
- 禁止一句话包含两个疑问 例如：宿舍电费怎么算，每个月大概多少钱 这类组合问句
- 禁止提问知识库未收录、无官方记载的冷门/衍生/主观体验类问题
- 禁止跳出指定话题范围提问无关内容

特别宽限：
- 如果问不出有明确资料可查询的问题，可以问已问过的问题

输出要求：
- 不列表、不编号、不解释
- 禁止知识库外无关问题
- 口语自然、随意、像真人随手发问
- 禁止重复或意思相近问题
- 只输出问题本身，无任何多余内容
- 询问同一个宿舍时，问题中省略掉宿舍名称
- 使用短句，也可以用口语碎片，但禁止书面化、模板化
- 禁止书面化、模板化
- 严格遵守单疑问原则，整句只能有一个查询重点
"""
prompt_q_easy = f"""

你是“测评问题生成器”，只模拟学生提问，绝对不回答问题。

规则：
1. 语言为 {language}。
2. 可使用宿舍别名/混写，如“宿舍x”“hall x”“xxx宿舍”。
3. 只输出纯问题，**绝对不要加任何个人想法、需求铺垫、理由说明**。
4. 不要出现“如果我想…”“我要…”“我比较在意…”这类自我描述。
5. 可包含价格、日期、数量等简单数字需求，不夹带已知数据。

6（最重要，优先完成这条）. 所有提问**严格限定在指定固定话题范围内**，仅可围绕以下内容出题：
SHRLO联系、Hall Charges、Room Types & Capacity、Hall Facilities、Admission Policy、Hall生活相关(访客通行、洗衣服务、空调、入住退房)、宿舍工作人员与导师信息、宿舍安全、消防规范、台风相关安排、宿舍活动、生活贴士、祈祷室、访客来访政策、空调使用、洗衣服务、GGT智能电表、本科生及研究生入住退宿流程与地点、多宿舍横向对比、宿舍环境、居住体验相关内容。

7. 禁止括号、抄写资料、书面化、模板化。
8. 询问同一个宿舍时，问题中省略掉宿舍名称
9. 只输出一条问题，禁止一次输出多个问题
10. 严格仅限**单一独立问题**，禁止复合问句、禁止用逗号拆分拼接两个提问、禁止一句话内含两个不同疑问点
11. 若上一轮回答明确说明知识库没有相关内容，立即放弃当前提问领域，更换全新独立领域出题，不继续追问同主题相关问题

【随机风格规则】
- 有概率不用“那、请问、有没有”开头
- 有概率省略句末问号
- 有概率不用标点
- 句式自然随机，禁止全部都是“那xxx嗎？”
- 有概率省略掉宿舍名称，直接问需求
- 有概率打乱语序

【绝对禁止】
- 禁止回答、禁止引用知识库
- 禁止解释、总结、说明
- 禁止出现“根据资料…”“答案是…”
- 禁止输出个人想法、需求前提、主观描述
- 禁止主动提供信息，只提问
- 禁止输出多条问题，只输出一条问题
- 禁止一句话包含两个疑问 例如：宿舍电费怎么算，每个月大概多少钱 这类组合问句
- 禁止提问知识库未收录、无官方记载的冷门/衍生/主观体验类问题
- 禁止跳出指定话题范围提问无关内容

特别宽限：
- 如果问不出有明确资料可查询的问题，可以问已问过的问题

输出要求：
- 不列表、不编号、不解释
- 禁止知识库外无关问题
- 口语自然、随意、像真人随手发问
- 禁止重复或意思相近问题
- 只输出问题本身，无任何多余内容
- 询问同一个宿舍时，问题中省略掉宿舍名称
- 使用短句，也可以用口语碎片，但禁止书面化、模板化
- 禁止书面化、模板化
- 严格遵守单疑问原则，整句只能有一个查询重点

"""

prompt_q_hard = f"""
你是“测评问题生成器”，只模拟学生提问，绝对不回答问题。

规则：
1. 语言为 {language}。
2. 可使用宿舍别名/混写，如“宿舍x”“hall x”“xxx宿舍”。
3. 只输出纯问题，**绝对不要加任何个人想法、需求铺垫、理由说明**。
4. 不要出现“如果我想…”“我要…”“我比较在意…”这类自我描述。
5. 可包含价格、日期、数量等简单数字需求，不夹带已知数据。
6（最重要，优先完成这条）. **所有提问严格锁定限定话题范围，仅允许围绕以下领域出题：**
SHRLO聯繫方式、宿舍收費標準、房型與容納人數、宿舍公共設施、入宿申請政策、宿舍日常起居（訪客通行、洗衣、空調、入住退宿流程）、宿舍職員與導師配置、宿舍安全管理、消防規範、颱風應對安排、宿舍活動、生活貼士、祈禱室、來訪人員政策、空調使用規則、洗滌服務、GGT智能電錶、本科生與研究生入住離校細節、多個hall差異對比、宿舍環境、居住體驗相關內容。
**禁止超出以上范围提问任何无关内容**。
7. 禁止括号、抄写资料、书面化、模板化。
8. 询问同一个宿舍时，问题中省略掉宿舍名称

【随机风格规则】
- 有概率不用“那、请问、有没有”开头
- 有概率省略句末问号
- 有概率不用标点
- 句式自然随机，禁止全部都是“那xxx嗎？”
- 有概率省略掉宿舍名称，直接问需求
- 有概率打乱语序
- 一次性输出两条至三条问题
- 句子可以连贯成一串，也可以独立成句但连续输出

【核心聚焦规则】
- 一次只围绕**同一个领域**提问，例如只问隔音、只问网络、只问设施、只问收费
- 延伸问题必须是**同一领域的递进/相关问题**，不跨领域、不杂糅无关内容
- 递进问题示例（同领域延伸）：
  - 隔音：隔音效果怎么样，吵到了该找谁投诉
  - 网络：网络稳不稳定，高峰期会不会卡顿掉线
  - 洗衣房：洗衣机够不够用，洗衣一次要多少钱
  - 床位：床有多宽，床垫需不需要自己带
  - 门禁：晚上几点关门，晚归能不能进
- 禁止同时出现隔音+网络+厨房+洗衣房这种多领域混合提问
- 两条问题必须满足以下其中一种组合：
  - 第一条：**知识库可检索到的已知信息**，第二条：**知识库无收录、无法检索到的延伸问题**
  - 或第一条：**知识库无收录、无法检索到的问题**，第二条：**知识库可检索到的已知信息**
- 已知信息举例：价格、房型、有无独卫、楼层、开放时间
- 无法检索信息举例：具体维修效率、某晚噪音情况、未来装修计划、个人入住感受

【绝对禁止】
- 禁止回答、禁止引用知识库
- 禁止解释、总结、说明
- 禁止出现“根据资料…”“答案是…”
- 禁止输出个人想法、需求前提、主观描述
- 禁止主动提供信息，只提问
- 禁止一次输出多个不同领域的问题
- 禁止换行
- 禁止跳出指定宿舍相关话题，問食堂、課程等無關內容

输出要求：
- 一次输出两条至三条问题，问题之间用标点符号隔开
- 所有问题必须属于**同一个主题领域**，彼此是延伸关系
- 不列表、不编号、不解释
- 禁止知识库外无关问题
- 口语自然、随意、像真人随手发问
- 禁止重复或意思相近问题
- 只输出问题本身，无任何多余内容
- 询问同一个宿舍时，问题中省略掉宿舍名称
- 可使用复杂长句，可以用短句，也可以用口语碎片，但禁止书面化、模板化
- 一定要在一行里输出，不要换行


"""


def generate_message(histories,tokens = 50)->str:
    """调用百炼应用生成文本回复。
    Generate a text response by calling the DashScope application.

    参数:
        histories: list[dict]，对话历史，元素包含 role/content。
    Arguments:
        histories: list[dict], conversation history with role/content fields.

    返回:
        str: 成功时返回模型输出文本。
    Returns:
        str: Model output text when the call succeeds.

    异常:
        RuntimeError: 失败后重试 3 次（每次间隔 10 秒）仍未成功。
    Raises:
        RuntimeError: Still fails after retries with 10-second intervals.
    """

    # 使用环境变量读取 DashScope / BAILIAN 应用 ID 与 API Key
    # Use environment variables for DashScope / BAILIAN app ID and API key
    app_id = os.getenv("BAILIAN_APP_ID", "")
    api_key = os.getenv("BAILIAN_API_KEY", "")

    last_error = None

    for attempt in range(1, 5):
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            ## 备用调用示例（当前未启用）
            ## Fallback call example (currently disabled)
            ##response: Any = Generation.call(model="qwen-plus", api_key=api_key, app_id=app_id, messages = histories, thinking_budget=tokens)
            future = executor.submit(Application.call, api_key=api_key, app_id=app_id, prompt=histories)
            try:
                response: Any = future.result(timeout=60)
            except FuturesTimeoutError as timeout_err:
                last_error = TimeoutError("百炼调用超时：超过 60 秒未返回。")
                print("百炼调用超时：超过 60 秒未返回，将重新发送请求。")
                future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
                raise last_error from timeout_err

            if response.status_code == HTTPStatus.OK:
                print(response.output.text)

                print("Output Token: ")
                print(response.usage.models[0].output_tokens)
                #print("Output Token: " + response.usage.models[2])

                return response.output.text

            last_error = RuntimeError(
                f"百炼调用失败: request_id={response.request_id}, code={response.status_code}, message={response.message}"
            )
            print(f'request_id={response.request_id}')
            print(f'code={response.status_code}')
            print(f'message={response.message}')
            print('请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code')
            if response.status_code == 502:
                print("检测到 502 Bad Gateway（上游临时故障），将自动重试。")

        except Exception as e:
            last_error = e
            print(f"错误信息：{e}")
            err_text = str(e)
            if "502 Bad Gateway" in err_text or "'code': 502" in err_text:
                print("检测到 502 Bad Gateway（上游临时故障），将自动重试。")
            print("请参考文档：https://help.aliyun.com/model-studio/developer-reference/error-code")
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        if attempt < 4:
            print(f"第 {attempt} 次调用失败，10 秒后重试...")
            time.sleep(10)

    raise RuntimeError("generate_message 调用失败：已重试 3 次，仍未成功。") from last_error


def generate_test_account(email,auto):
    """生成测试账号的函数。
    Create a test account with generated persona and profile.
    包括生成 uid、character 和 profile，并将它们与 email 一起存储到 bot_profile 表中。
    It generates uid, character, and profile, then stores them with email into bot_profile.

    参数:
        email: str，测试账号的邮箱。
    Arguments:
        email: str, email for the test account.

    返回:
        true if account created successfully, False otherwise.
    Returns:
        True if the account is created successfully, otherwise False.
    """

    
    profile_msg = generate_profile()
    profile_json = Helper.transform_profile_to_json(profile_msg)
    print("Profile generated:", profile_json)

    if not profile_json:
        print("生成用户画像失败，无法创建测试账号。")
        return None

    try:
        # 密码由环境变量控制，便于替换和安全管理
        # The test account password is controlled via an environment variable for safety
        test_password = os.getenv("TEST_ACCOUNT_PASSWORD", "123456")
        uid = supabase_client.auth.admin.create_user({
        "email": email,
        "password": test_password,
        "email_confirm": True}).user.id
    except Exception as e:
        print(f"创建用户失败: {e}")
        return None

    if not uid:
        print("创建用户失败，无法获取 UID。")
        return None

    character = profile_json["character"]
    generated_profile = profile_json["profile"]
    print(f"Generated character: {character}")
    print(f"Generated profile: {generated_profile}")

    ## 人工审查已生成的用户人设与画像，确保其合理性与多样性，符合测试需求。审查不通过的可以重新生成。
    ## Manually review generated persona/profile; regenerate if it does not meet testing needs.
    while True and not auto:
        print(f"请审查以下生成的用户人设与画像，确保其合理性与多样性，符合测试需求。审查不通过的将重新生成。\n人设: {character}\n画像: {generated_profile}")
        user_input = input("请输入 'y' 通过审查，输入其他内容重新生成：")
        if user_input.lower() == 'y':
            break
        else:
            profile_msg = generate_profile(user_input)
            profile_json = Helper.transform_profile_to_json(profile_msg)
            character = profile_json["character"]
            generated_profile = profile_json["profile"]
    
    # 将生成的 uid、character 和 profile 存储到 bot_profile 表中
    # Store generated uid, character, and profile into the bot_profile table.
    data = {
        "email": email,
        "uid": uid,
        "character": character,
        "profile": generated_profile
    }
    response = supabase_client.table("bot_profile").insert(data).execute()
    print("Database insert response:", response.data[0]["email"], response.data[0]["uid"])
    
    print(f"测试账号 {email} 创建成功，uid: {uid}")
    return True

def search_by_uid(uid)-> tuple[list, list]:
    """按用户 UID 查询聊天记录与用户画像。
    Query chat logs and user profile by UID.

    参数:
        uid: str，用户唯一标识。
    Arguments:
        uid: str, unique user identifier.

    返回:
        tuple[list, list]: (chat_logs, profiles)。
    Returns:
        tuple[list, list]: (chat_logs, profiles).
    """
    
    # 按 id 升序排序聊天记录，保证对话顺序正确。
    # Sort chat logs by id in ascending order to keep conversation order correct.
    chatlog = supabase_client.table("chat_logs").select("*").eq("user_id", uid).order("id").execute()

    profile = supabase_client.table("profiles").select("*").eq("user_id", uid).execute()

    return chatlog.data, profile.data

import random

def transform_latest_histories(histories, character = "",asked_qs = [],comment = "",is_easy = True):
    """将原始聊天历史转换为问题生成器使用的对话格式。
    Transform raw chat history into the message format for question generation.

    参数:
        histories: list[dict]，数据库返回的历史消息。
        character: str，用户人设补充信息。
        asked_qs: str，已提过的问题列表字符串。
    Arguments:
        histories: list[dict], history messages returned from database.
        character: str, optional persona text.
        asked_qs: str, serialized list of asked questions.
    返回:
        list[dict]: 可直接传给问题生成模型的 messages 列表。
    Returns:
        list[dict]: message list consumable by the question generator.
    """
    # 按 id 排序历史记录。
    # Sort histories by id.

    if is_easy:
        # 在 easy 与 compare 提示词之间随机选择。
        # Randomly choose between easy and compare prompts.
            if random.random() < 0.5:
                prompt_q = prompt_q_easy
            else:
                prompt_q = prompt_q_compare
    
    else:
        prompt_q = prompt_q_hard
        
    histories = sorted(histories, key=lambda x: x["id"])

    all_questions = get_all_questions() or []
    sample_size = len(all_questions)
    sampled_questions = random.sample(all_questions, sample_size) if sample_size > 0 else []
    asked_qs = sampled_questions
    asked_qs = str(asked_qs)
    character_info = f"/no_think 请严格按照下面的用户人设、使用语言、说话习惯来生成问题，完全模仿其语气： {character}。" if character else "无特定人设"
    asked_questions = f"禁止问题重复或意思相近的问题,重复范畴不包括宿舍名称。 历史问题包括: {asked_qs}。"
    comment = f"这是测试者的备注,优先考虑这里的（最重要）：{comment}" if comment else "无备注"
    question_histories = [{"role": "system", "content": character_info + prompt_q + asked_questions + comment}, {"role": "user", "content": "你好！歡迎來到香港科技大學宿舍咨詢助手服務，請問你有什麼關於宿舍的問題需要幫助嗎？"}]
    for i,h in enumerate(histories):
        if h["role"] == "assistant":
            question_histories.append({"role": "user", "content": h["content"]})
        else:
            question_histories.append({"role": "assistant", "content": h["content"]})
    return question_histories


def get_email_to_uid():
    """获取邮箱到用户 UID 的映射。
    Get mapping from email to user UID.

    返回:
        dict: {email: uid} 的映射字典。
    Returns:
        dict: mapping dictionary of {email: uid}.
    """
    data = supabase_client.table("bot_profile").select("email", "uid").execute()
    ## 获取唯一的 email-uid 对。
    ## Get unique email-uid pairs.
    unique_pairs = {(item["email"], item["uid"]) for item in data.data}
    email_to_uid = {email: uid for email, uid in unique_pairs}
    return email_to_uid

def get_email_to_profile():
    """获取邮箱到用户画像的映射。
    Get mapping from email to user profile.

    返回:
        dict: {email: profile(dict)} 的映射字典。
        Profile 是一个字典，包含 Gender、Identity、Priority Factors、Preferred Room Type、Budget (Yearly)、Additional Remarks 等字段。
    Returns:
        dict: mapping dictionary of {email: profile(dict)}.
        Profile includes fields like Gender, Identity, priorities, room type, budget, and remarks.
    """

    data = supabase_client.table("bot_profile").select("email", "profile").execute()
    ## 获取唯一的 email-profile 对。
    ## Get unique email-profile pairs.
    unique_pairs = {(item["email"], str(item["profile"])) for item in data.data}
    email_to_profile = {email: eval(profile) for email, profile in unique_pairs}

    return email_to_profile

def get_email_to_character():
    """获取邮箱到用户人设的映射。
    Get mapping from email to user persona.

    返回:
        dict: {email: character} 的映射字典。
    Returns:
        dict: mapping dictionary of {email: character}.
    """
    data = supabase_client.table("bot_profile").select("email", "character").execute()
    ## 获取唯一的 email-character 对。
    ## Get unique email-character pairs.
    unique_pairs = {(item["email"], item["character"]) for item in data.data}
    email_to_character = {email: character for email, character in unique_pairs}
    return email_to_character

def get_all_questions():
    """ 获取所有Bot用户的提问历史。
    Get all asked-question history from bot users.
    
    参数:
        email_to_uid: dict，邮箱到用户 UID 的映射。
    Arguments:
        email_to_uid: dict, mapping from email to UID.
        
    返回:
        list[str]: 所有用户的提问历史列表。
    Returns:
        list[str]: asked-question history of all users.
    """
    
    # 根据 email_to_uid 映射查找所有用户 UID。
    # Find all users' uids based on email_to_uid mapping.
    data = supabase_client.table("bot_histories").select("question").execute()
    all_questions = [clean_question(item["question"] )for item in data.data if item["question"]]  # 过滤掉空问题
    # Filter out empty questions.
    return all_questions

def get_all_character():
    """ 获取所有Bot用户的人设信息。
    Get persona information for all bot users.
    
    参数:
        email_to_uid: dict，邮箱到用户 UID 的映射。
    Arguments:
        email_to_uid: dict, mapping from email to UID.
        
    返回:
        list[str]: 所有用户的人设信息列表。
    Returns:
        list[str]: persona list for all users.
    """
    
    # 根据 email_to_uid 映射查找所有用户 UID。
    # Find all users' uids based on email_to_uid mapping.
    data = supabase_client.table("bot_profile").select("character").execute()
    all_character = [item["character"] for item in data.data if item["character"]]  # 过滤掉空人设
    # Filter out empty personas.
    return all_character

def generate_profile(comment:str = ""):
    data = get_all_character()
    """生成用于前端自动填表的用户人设与结构化画像。
    Generate persona and structured profile for frontend auto form filling.

    参数:
        data: str，已有人设摘要，用于避免重复生成相似画像。
    Arguments:
        data: str, existing persona summary used to avoid similar generation.

    返回:
        str | None: 模型返回的 JSON 字符串文本。
    Returns:
        str | None: JSON string returned by the model.
    """
    # 使用画像生成提示词。
    # Use profile-generation prompt.
    prompt = prompt_p
    profile_msg = generate_message([{"role": "system", "content": "必须先考虑以下的建议："+ comment + ";" +prompt + "; 不要生成类似或相近的人设，已生成过的人设摘要包括：" + str(data)}],300)

    return profile_msg


def clean_question(question:str)->str:
    """清洗问题文本，去除多余空格、特殊字符等。
    Clean question text by removing unrelated wrappers and noise.

    参数:
        question: str，原始问题文本。
    Arguments:
        question: str, raw question text.

    返回:
        str: 清洗后的问题文本。
    Returns:
        str: cleaned question text.
    """
    # 仅保留 [User Question] 与 [Recent Conversation History] 之间的部分。
    # Keep only the part between [User Question] and [Recent Conversation History].

    cleaned = question.split("[User Question]\n")[-1].strip()
    cleaned = cleaned.split("\n\n[Recent Conversation History]\n")[0].strip()
    
    return cleaned

def clean_history(question:str)->str:
    """清洗历史对话文本，去除多余空格、特殊字符等。
    Clean conversation history text payload.

    参数:
        question: str，原始历史对话文本。
    Arguments:
        question: str, raw conversation-history text.

    返回:
        str: 清洗后的历史对话文本。
    Returns:
        str: cleaned conversation-history text.
    """
    if "[Recent Conversation History]\n" not in question:
        return ""
    cleaned = question.split("[Recent Conversation History]\n")[-1].strip()
    return cleaned