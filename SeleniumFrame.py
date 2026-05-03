## 以下是自动填表相关的 Selenium 代码，针对不同字段类型（按钮、下拉、文本输入）进行智能匹配和操作。
## The Selenium code below handles auto form filling with smart matching for different field types.
import os
import subprocess
from typing import Any
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

driver: Any = None
wait: Any = None


def _normalize_key_text(value):
    """标准化字段名文本，便于大小写与下划线兼容匹配。
    Normalize field-key text for case-insensitive and underscore-compatible matching.
    """
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _build_field_aliases(field_key):
    """为同一字段生成别名集合，兼容 DB/API 与前端标签命名差异。
    Build alias set for one field to bridge naming gaps between DB/API and frontend labels.
    """
    key_norm = _normalize_key_text(field_key)
    alias_map = {
        "gender": ["Gender"],
        "identity": ["Identity"],
        "budget": ["Budget (Yearly)", "Budget"],
        "budget range": ["Budget (Yearly)", "Budget"],
        "budget yearly": ["Budget (Yearly)", "Budget"],
        "budget_range": ["Budget (Yearly)", "Budget"],
        "room types": ["Preferred Room Type", "Room Type"],
        "room type": ["Preferred Room Type", "Room Type"],
        "room_types": ["Preferred Room Type", "Room Type"],
        "priority factors": ["Priority Factors", "Priorities"],
        "priorities": ["Priority Factors", "Priorities"],
        "additional remarks": ["Additional Remarks", "Additional Info"],
        "additional info": ["Additional Remarks", "Additional Info"],
        "additional_info": ["Additional Remarks", "Additional Info"],
    }

    candidates = {key_norm}
    for alias in alias_map.get(key_norm, []):
        candidates.add(_normalize_key_text(alias))
    return candidates


def bind_selenium_context(driver_instance, wait_instance=None, timeout=20):
    """绑定全局 driver/wait，供简化调用场景复用。
    Bind global driver/wait so helper calls can reuse shared Selenium context.
    """
    global driver, wait
    driver = driver_instance
    wait = wait_instance if wait_instance is not None else WebDriverWait(driver_instance, timeout)


def _require_driver(web_driver=None):
    active_driver = web_driver or driver
    if active_driver is None:
        raise RuntimeError("Selenium driver 未初始化。请先调用 bind_selenium_context(...) 或传入 web_driver 参数。")
    return active_driver


def _require_wait(waiter=None):
    active_wait = waiter or wait
    if active_wait is None:
        raise RuntimeError("Selenium wait 未初始化。请先调用 bind_selenium_context(...) 或传入 waiter 参数。")
    return active_wait

    
def build_chrome_driver(chrome_options):
    """直接使用 webdriver_manager 启动，避免 Selenium Manager 在部分环境卡住。
    Start Chrome via webdriver_manager to avoid Selenium Manager stalls in some environments.
    """
    print("[STEP 0] 使用 webdriver_manager 启动...")
    driver_path = ChromeDriverManager().install()
    print(f"[STEP 0] chromedriver 路径: {driver_path}")

    try:
        os.chmod(driver_path, 0o755)
        print("[STEP 0] 已设置驱动可执行权限")
    except Exception as chmod_err:
        print(f"[STEP 0] 设置权限失败(继续尝试): {chmod_err}")

    try:
        subprocess.run(
            ["xattr", "-d", "com.apple.quarantine", driver_path],
            check=False,
            capture_output=True,
            text=True,
        )
        print("[STEP 0] 已尝试移除驱动 quarantine")
    except Exception as xattr_err:
        print(f"[STEP 0] 移除 quarantine 失败(继续尝试): {xattr_err}")

    service = Service(driver_path)
    drv = webdriver.Chrome(service=service, options=chrome_options)
    print("[STEP 0] webdriver_manager 启动成功")
    return drv

def normalize_values(value):
    """统一字段值格式，确保后续按列表处理。
    Normalize field values so downstream logic can always process a list.
    """
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()] if str(value).strip() else []

def find_field_container(field_key, waiter=None):
    """先按字段别名匹配 label，再返回其父 div 容器。
    Match label by aliases first, then return its parent div container.
    """
    active_wait = _require_wait(waiter)
    wanted_aliases = _build_field_aliases(field_key)

    labels = active_wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "label")))
    for label in labels:
        label_text = _normalize_key_text(label.text)
        if not label_text:
            continue
        if any(alias in label_text or label_text in alias for alias in wanted_aliases):
            return label.find_element(By.XPATH, "./ancestor::div[1]")

    raise TimeoutException(f"找不到字段容器: {field_key}")

def click_text_candidate(container, target, web_driver=None):
    """在同一个父 div 里按文本匹配按钮并点击（保持原逻辑）。
    Find a text-matched button in the same parent div and click it.
    """
    active_driver = _require_driver(web_driver)
    target_norm = target.strip().lower()
    candidates = container.find_elements(By.XPATH, ".//*[self::button or @role='button']")
    for el in candidates:
        txt = (el.text or "").strip()
        if not txt:
            continue
        txt_norm = txt.lower()
        if txt_norm == target_norm or target_norm in txt_norm or txt_norm in target_norm:
            try:
                active_driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                el.click()
                return True
            except Exception:
                continue
    return False

def select_from_parent_div(container, target):
    """在同一个父 div 内找 select，并选择与 target 匹配的 option。
    Find a select in the same parent div and choose an option matching target.
    """
    selects = container.find_elements(By.TAG_NAME, "select")
    if not selects:
        return False

    for sel in selects:
        try:
            select_obj = Select(sel)
            select_obj.select_by_visible_text(target)
            return True
        except Exception:
            for opt in sel.find_elements(By.TAG_NAME, "option"):
                opt_text = (opt.text or "").strip()
                if opt_text and (target == opt_text or target in opt_text or opt_text in target):
                    opt.click()
                    return True
    return False

def fill_text_input(container, value):
    """向容器中的文本输入控件写入内容。
    Fill textarea/input controls inside the container.
    """
    textareas = container.find_elements(By.TAG_NAME, "textarea")
    if textareas:
        textareas[0].clear()
        textareas[0].send_keys(value)
        return True

    inputs = container.find_elements(By.XPATH, ".//input[not(@type='checkbox') and not(@type='radio')]")
    if inputs:
        inputs[0].clear()
        inputs[0].send_keys(value)
        return True

    return False

def set_profile_field(field_key, field_value, waiter=None, web_driver=None):
    """按字段类型执行自动填表策略。
    Apply auto-fill strategy according to field type.

    流程:
    1) 找 key 对应父 div
    2) 在同一父 div 里优先 select->option
    3) 失败再按原 button 逻辑
    Flow:
    1) Locate parent div by field key
    2) Prefer select->option within the same div
    3) Fallback to original button click logic
    """
    key_norm = _normalize_key_text(field_key)
    container = find_field_container(field_key, waiter=waiter)
    values = normalize_values(field_value)
    if not values:
        return False

    if key_norm in {"additional remarks", "additional info", "additional_info"}:
        return fill_text_input(container, " ".join(values))

    if isinstance(field_value, list):
        all_ok = True
        for v in values:
            matched = select_from_parent_div(container, v) or click_text_candidate(container, v, web_driver=web_driver)
            if not matched:
                print(f"未匹配到选项: {field_key} -> {v}")
                all_ok = False
        return all_ok

    # 单值：文本框 -> select/option -> button。
    # Single value order: text input -> select/option -> button.
    return fill_text_input(container, values[0]) or select_from_parent_div(container, values[0]) or click_text_candidate(container, values[0], web_driver=web_driver)