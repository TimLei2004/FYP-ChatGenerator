
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from SeleniumFrame import build_chrome_driver, set_profile_field, bind_selenium_context
from Helper import transform_profile_to_json
import UpdateBotHistories
from GenerateMessage import generate_message, generate_test_account, search_by_uid, get_email_to_uid, get_email_to_character, get_email_to_profile, generate_profile, transform_latest_histories
from GenerateMessage import get_all_questions

def start_a_test(email:str, auto:bool = True):
    """开始一个测试的函数。包括生成测试账号、查询历史记录、生成问题等步骤。
    Start one end-to-end test flow, including account creation, history query, and question generation.
    """
    # 1. 检测账号是否存在，若不存在则创建。
    # 1. Check whether the account exists; create it if missing.
    email_to_uid = get_email_to_uid()
    if email not in email_to_uid:
        print(f"账号 {email} 不存在，正在创建...")
        is_success = generate_test_account(email,auto)
        if not is_success:
            print("账号创建失败，无法继续测试流程。")
            return
        
    else:
        print(f"账号 {email} 已存在，继续测试流程...")

    email_to_uid = get_email_to_uid()
    # 2. 根据 email 获取 uid。
    # 2. Get uid by email.
    uid = email_to_uid[email]
    print(f"用户 UID: {uid}")
    # 3. 查询该用户的聊天记录和人设。
    # 3. Query chat logs and persona for this user.
    chat_logs, profiles = search_by_uid(uid)
    print(f"Chat logs: {chat_logs}")
    print(f"Profiles: {profiles}")

# ------------------- # 以下为测试流程的 Selenium 自动化脚本，包含详细的步骤说明与日志输出，便于调试与验证。# --------------------------------------------------- #
# ------------------- # The Selenium automation script below includes detailed step logs for debugging and validation. # --------------------------------------------------- #

    print("[STEP 0] 初始化浏览器配置...")
    # -----------------------------
    # 0) 浏览器初始化
    # 0) Browser initialization
    # -----------------------------
    # 关闭 Chrome 密码管理与弱密码检测提示，避免弹窗打断 Selenium 元素定位。
    # Disable password manager and leak detection to avoid popups interrupting element locating.
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-features=PasswordLeakDetection,PasswordCheck")
    options.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
        },
    )

    driver = build_chrome_driver(options)
    wait = WebDriverWait(driver, 20)
    bind_selenium_context(driver, wait)
    print("[STEP 0] 浏览器启动完成")

    # -----------------------------
    # 1) 测试参数准备
    # 1) Prepare test parameters
    # -----------------------------
    print("[STEP 1] 准备测试参数与历史记录...")
    url = "https://aidormadvisor.timngan.xyz/"

    account = email
    # 密码由环境变量控制，便于替换和安全管理
    # The test account password is controlled via an environment variable for safety
    password = os.getenv("TEST_ACCOUNT_PASSWORD", "123456")
    character = ""

    # 先读取当前聊天记录与画像状态，后续用于判断是否需要自动填表。
    # Read current histories/profile first to determine whether auto form filling is needed.
    histories, profile = search_by_uid(uid)
    print(f"[STEP 1] 当前历史消息数: {len(histories)}")

    # -----------------------------
    # 2) 打开站点并执行登录
    # 2) Open site and perform login
    # -----------------------------
    print("[STEP 2] 打开网站...")
    driver.get(url)
    print("[STEP 2] 网站已打开，准备点击登录按钮")

    # 2.1 点击首页登录入口。
    # 2.1 Click login entry on homepage.
    login_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Login with School Account')]")
        )
    )
    login_button.click()
    print("[STEP 2.1] 已点击 Login with School Account")

    # 2.2 输入账号密码。
    # 2.2 Input account and password.
    email_field = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='Your gmail or ITSC email']")
        )
    )
    email_field.clear()
    email_field.send_keys(account)
    print(f"[STEP 2.2] 已输入账号: {account}")

    password_field = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='password']"))
    )
    password_field.clear()
    password_field.send_keys(password)
    print("[STEP 2.2] 已输入密码")

    # 2.3 勾选数据政策并提交登录。
    # 2.3 Check data-policy box and submit login.
    checkbox = wait.until(EC.element_to_be_clickable((By.ID, "ack-data-policy")))
    checkbox.click()
    password_field.send_keys(Keys.RETURN)
    print("[STEP 2.3] 已勾选政策并提交登录")

    # 兼容分支：如果页面仍停留在登录页，尝试点击 Enter System 按钮继续。
    # Compatibility branch: if still on login page, try clicking Enter System.
    try:
        enter_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        enter_button.click()
        print("[STEP 2.4] 检测到二次提交按钮，已点击 Enter System")
    except Exception:
        print("[STEP 2.4] 未出现二次提交按钮，跳过")

    # -----------------------------
    # 3) 首次用户自动填表
    # 3) Auto-fill form for first-time users
    # -----------------------------
    # 重新读取 profile，避免使用登录前的旧状态。
    # Reload profile to avoid stale pre-login state.
    print("[STEP 3] 检查是否需要首次填表...")
    chatlog, profile = search_by_uid(uid)
    character = ""

    loaded_characters = get_email_to_character()
    loaded_profiles = get_email_to_profile()

    if profile[0]["form_preferences"] == {}:
        print("[STEP 3] 检测到空画像，进入自动填表流程")
        # 优先Supabase的人设与画像，减少模型调用与不稳定性。
        # Prefer persona/profile from Supabase to reduce model calls and instability.
        if account in loaded_characters and account in loaded_profiles:
            character = loaded_characters[account]
            generated_profile = loaded_profiles[account]
            print("[STEP 3.1] 已从Supabase 加载 character/profile")
        else:
            print("[STEP 3.1] Supabase，开始生成 profile...")
            profile_msg = generate_profile()
            profile_json = transform_profile_to_json(profile_msg)
            print("Profile generated:", profile_json)

            print("[STEP 3.1] 已从Supabase 加载 character/profile")
            print("[STEP 3.1] profile 生成完成")

        loaded_characters = get_email_to_character()
        loaded_profiles = get_email_to_profile()
        character = loaded_characters[account]
        generated_profile = loaded_profiles[account]
        
        # 按字段逐项填充前端表单。
        # Fill frontend form field by field.
        print("[STEP 3.2] 开始逐字段填写前端表单")
        is_error = False

        for key, value in generated_profile.items():
            print(f"[STEP 3.2] Processing {key}: {value}")
            try:
                success = set_profile_field(key, value, waiter=wait, web_driver=driver)
                if success:
                    print(f"[STEP 3.2] Filled {key} successfully")
                else:
                    print(f"[STEP 3.2] Failed to fill {key}")
            except Exception as e:
                print(f"[STEP 3.2] 填写字段异常 {key}: {e}")

        if is_error:
            print("[STEP 3.2] 填表过程中出现错误")
            return

        print("[STEP 3.3] 用户确认完成，准备提交画像表单")

        # 提交画像表单，进入聊天页面。
        # Submit profile form and enter chat page.
        submit_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(., 'Start Chat Recommendation')]")
            )
        )
        submit_button.click()
        print("[STEP 3.3] 已点击 Start Chat Recommendation")
    else:
        print("[STEP 3] 已存在画像，跳过自动填表")


    # -----------------------------
    # 4) 进入聊天并开始问答回归测试
    # 4) Enter chat and start Q&A regression test
    # -----------------------------

    email_2_uid = get_email_to_uid()


    print("[STEP 4] 等待聊天输入框出现...")
    chat_input_locator = (
        By.XPATH,
        "//input[contains(@placeholder, 'Ask about dorms')]",
    )
    wait.until(EC.presence_of_element_located(chat_input_locator))
    print("[STEP 4] Login successful! 已进入聊天页")

    asked_qs = get_all_questions()
    print(f"[STEP 4] 已加载历史问题数: {len(asked_qs)}")


    # 循环发送问题并等待 assistant 回答落库。
    # Send questions in loop and wait for assistant replies to persist.
    round_idx = 0
    comment = " "
    while len(histories) / 2 < 10:
        round_idx = len(histories) // 2 + 1
        print(f"[STEP 5][Round {round_idx}] 准备生成并发送问题...")
        qa_input = wait.until(EC.element_to_be_clickable(chat_input_locator))

        ## 生成问题时附加当前测试建议，改变bot输出以适应测试场景。共等待五秒，让测试人员有时间修改备注信息。
        ## Append tester comments when generating questions so output matches the test scenario.
        if not auto:
            comment = input(f"请输入本轮测试建议（回车继续，当前备注: {comment}）:")


        ## 从第八轮开始，问困难问题，测试模型的极限表现，并观察是否有崩溃或严重错误的情况出现。
        ## From round 8, ask harder questions to stress-test model behavior and stability.
        if round_idx >= 8:
            
            question_histories = transform_latest_histories(histories, character, asked_qs, comment, False)
        else:     
            question_histories = transform_latest_histories(histories, character, asked_qs, comment, True)

        msg = generate_message(question_histories)

        qa_input.send_keys(msg)
        qa_input.send_keys(Keys.RETURN)
        asked_qs.append(msg)
        print(f"[STEP 5][Round {round_idx}] 问题已发送: {msg}")

        # 轮询数据库，直到出现新的 assistant 回复。
        # Poll database until a new assistant reply appears.
        poll_count = 0
        while True:
            poll_count += 1
            new_histories, _ = search_by_uid(uid)
            if len(new_histories) > len(histories) and new_histories[-1]["role"] == "assistant":
                print(f"[STEP 5][Round {round_idx}] 收到新回复（轮询 {poll_count} 次）")
                print(new_histories[-1])
                histories = new_histories
                break
            print(f"[STEP 5][Round {round_idx}] Waiting for answer...（轮询 {poll_count}）")
            time.sleep(2)

            ## 为了避免死循环，设置一个最大轮询次数，超过后跳出循环并记录日志。
            ## To avoid infinite loops, stop polling after a max count and log warning.
            if poll_count >= 20:
                print(f"[STEP 5][Round {round_idx}] 警告：轮询超过20次仍未收到回复，跳出等待循环")
                UpdateBotHistories.update_one_bot_histories(email)
                break

    UpdateBotHistories.update_one_bot_histories(email)
    print("[DONE] 自动登录与问答测试流程结束")
    ## 关闭浏览器。
    ## Close browser.
    driver.quit()


def _run_single_test(email: str, auto: bool = True):
    """线程任务包装：执行单账号测试并返回结果。
    Thread-task wrapper: run a single-account test and return result.
    """
    try:
        start_a_test(email, auto=auto)
        return email, True, None
    except Exception as e:
        return email, False, str(e)


def start_tests_parallel(emails, auto: bool = True, max_workers: int = 2):
    """并发执行测试账号，默认双线程。
    Run account tests concurrently, defaulting to two workers.
    """
    if not emails:
        print("[PARALLEL] 邮箱列表为空，未执行任务")
        return {}

    max_workers = max(1, int(max_workers))
    print(f"[PARALLEL] 开始并发测试，线程数: {max_workers}，任务数: {len(emails)}")

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_single_test, email, auto): email for email in emails
        }
        for future in as_completed(futures):
            email = futures[future]
            try:
                _, ok, err = future.result()
                results[email] = {"success": ok, "error": err}
                if ok:
                    print(f"[PARALLEL] {email} 测试完成")
                else:
                    print(f"[PARALLEL] {email} 测试失败: {err}")
            except Exception as e:
                results[email] = {"success": False, "error": str(e)}
                print(f"[PARALLEL] {email} 任务异常: {e}")

    success_count = sum(1 for v in results.values() if v["success"])
    print(f"[PARALLEL] 全部完成，成功 {success_count}/{len(results)}")
    return results
