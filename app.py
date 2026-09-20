def renew_service(page):
    try:
        log("➡ 进入续期流程...")
        if page.url != SERVICE_URL:
            page.goto(SERVICE_URL, wait_until="domcontentloaded", timeout=60000)
        handle_cloudflare(page)

        log("🖱️ 准备点击 'Renew' 按钮...")
        # 优化 1: 增加 :visible 伪类并取第一个，严格过滤掉隐藏元素
        renew_btn = page.locator('button:has-text("Renew"):visible').first
        create_btn = page.locator('button:has-text("Create Invoice"):visible').first

        modal_opened = False
        for i in range(3):
            try:
                renew_btn.wait_for(state="visible", timeout=10000)
                renew_btn.scroll_into_view_if_needed()
                
                # 优化 2: 强制等待，确保按钮的 JS 监听器已加载
                time.sleep(2)
                
                # 优化 4: 截取点击前的屏幕快照用于排查遮挡问题
                page.screenshot(path=f"debug_before_click_{i+1}.png")
                
                log(f"🖱️ 第 {i+1} 次尝试点击 'Renew'...")
                # 优化 3: 使用 JavaScript 原生强制点击，无视透明遮罩或拦截
                renew_btn.evaluate("el => el.click()")

                # 等待检测是否出现“未到续期时间”弹窗
                time.sleep(3)
                page_text = page.locator("body").inner_text()
                if "Renewal Restricted" in page_text or "can only renew" in page_text.lower():
                    log("⚠️ 未到续期时间，无法续期。")
                    page.screenshot(path="renew_not_allowed.png")
                    return "NOT_TIME"   # 特殊状态

                log("🖲️ 等待弹窗出现...")
                try:
                    create_btn.wait_for(state="visible", timeout=5000)
                    modal_opened = True
                    log("✅ 弹窗已成功弹出！")
                    break
                except:
                    log("⚠️ 弹窗未出现，可能是点击未响应，准备重试...")
                    page.screenshot(path=f"debug_modal_failed_{i+1}.png")
            except Exception as e:
                log(f"❌ 点击尝试出错: {e}")

        if not modal_opened:
            log("❌ 错误：尝试多次后，续费弹窗仍未出现。")
            page.screenshot(path="renew_modal_failed.png")
            return False

        handle_cloudflare(page)
        log("🖱️ 点击 'Create Invoice'...")
        # 同样对 Create Invoice 按钮使用 JS 强制点击
        create_btn.evaluate("el => el.click()")

        new_invoice_url = None
        start_wait = time.time()
        while time.time() - start_wait < 90:
            if "/payment/invoice/" in page.url:
                new_invoice_url = page.url
                log(f"🎉 页面已跳转: {new_invoice_url}")
                break
            if page.locator('iframe[src*="challenges.cloudflare.com"]').count() > 0:
                log("⚠️ 遇到拦截，尝试处理...")
                handle_cloudflare(page)
            time.sleep(1)

        if not new_invoice_url:
            log("❌ 未能进入发票页面，超时。")
            page.screenshot(path="renew_stuck_invoice.png")
            return False

        if page.url != new_invoice_url:
            page.goto(new_invoice_url)
        handle_cloudflare(page)

        log("🔎 查找 'Pay' 按钮...")
        pay_btn = page.locator('a:has-text("Pay"):visible, button:has-text("Pay"):visible').first
        pay_btn.wait_for(state="visible", timeout=30000)
        
        # 支付按钮同样使用强制点击以提升稳定性
        pay_btn.evaluate("el => el.click()")
        log("✅ 'Pay' 按钮已点击。")

        # 等待支付确认页面或跳转回服务页
        time.sleep(5)
        # 返回服务管理页面以获取新的到期时间
        page.goto(SERVICE_URL, wait_until="domcontentloaded", timeout=60000)
        handle_cloudflare(page)
        return True

    except Exception as e:
        log(f"❌ 续费异常: {e}")
        page.screenshot(path="renew_error.png")
        return False
