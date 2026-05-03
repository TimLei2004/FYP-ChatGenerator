
import supabase
import os
from GenerateMessage import search_by_uid, get_email_to_uid, get_email_to_character, get_email_to_profile, generate_profile



def update_one_bot_histories(email):
    uid = get_email_to_uid()[email]
    character = get_email_to_character()[email]
    profile = get_email_to_profile()[email]
    chatlog, _ = search_by_uid(uid)
    question = ""
    answer = ""

    nullData = {
        "email": email,
        "uid": uid,
        "character": character,
        "profile": profile,
        "question": None,
        "answer": None,
        "history_sent": None,
        "inferred_preference_sent": None
        }
    print(profile)
    ## 按 id 升序排序 chatlog，确保问题顺序正确。
    ## Sort chatlog by id ascending to keep question order correct.
    chatlog = sorted(chatlog, key=lambda x: x['id'])

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

    data = nullData.copy()

    for item in chatlog:
        if item['role'] == 'user' and item['user_id'] == uid:
            data['question'] = item['history_sent'][-1]['content'] if item['history_sent'] else ""
            data['history_sent'] = item['history_sent']
            data['inferred_preference_sent'] = item['inferred_preferences_sent']

        elif item['role'] == 'assistant' and item['user_id'] == uid and data['question']:
            data['answer'] = item['content']
            id = search_QA_is_exist(uid, data['question'], data['answer'])
            if id != -1:
                print(f"QA pair already exists for uid: {uid}, id: {id}. Skipping insertion.")
            else:
                response = supabase_client.table("bot_histories").insert(data).execute()
                print(f"Inserted QA pair for uid: {uid}, id: {response.data[0]['id']}.")
            data = nullData.copy()

    


def update_all_bot_histories():
    """"
    Update the bot_histories table with the given parameters. The function will insert a new record
    使用给定参数更新 bot_histories 表，该函数会插入新记录。
    Update bot_histories with given parameters; this function inserts new records.
    
    Table definition:
        email text not null,
        uid text null,
        character text not null,
        profile jsonb null,
        question text null,
        answer text null,
        history_sent jsonb null,
        inferred_preference_sent jsonb null,
        
    """

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    email_to_uid = get_email_to_uid()
    for email in email_to_uid.keys():
        update_one_bot_histories(email)
 


def get_all_bot_histories():
    """"
    Get all records from the bot_histories table. The function will return a list of dictionaries, each dictionary represents a record in the table.
    获取 bot_histories 表中的所有记录。函数返回字典列表，每个字典代表一条记录。
    Get all records from bot_histories and return a list of dictionaries.
    """
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase_client.table("bot_histories").select("*").execute()
    return response.data


def search_QA_is_exist(uid,question, answer):
    """"
    Search for a specific question and answer pair in the bot_histories table for a given user ID. The function will return True if the pair exists, otherwise False.
    在指定用户的 bot_histories 中查找问题-回答对；存在则返回对应 id，不存在返回 -1。
    Search QA pair for a given user in bot_histories; return id if found, otherwise -1.
    """
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase_client.table("bot_histories").select("id").eq("uid", uid).eq("question", question).eq("answer", answer).execute()
    if len(response.data) > 0:
        return response.data[0]['id']
    else: 
        return -1