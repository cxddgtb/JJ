# 基金短线买卖大模型 - GitHub推送指南

本指南将帮助您将项目代码推送到GitHub仓库。

## 前提条件
1. 已安装Git（可从 https://git-scm.com/ 下载安装）
2. 已注册GitHub账号
3. 已在GitHub上创建了一个新仓库

## 步骤1: 配置推送脚本
1. 打开文件 `easy_push.ps1`
2. 替换以下信息为您自己的GitHub信息:
   ```powershell
   $githubRepoUrl = "https://github.com/您的用户名/您的仓库名.git"
   $yourName = "您的姓名"
   $yourEmail = "您的邮箱@example.com"
   ```

## 步骤2: 运行推送脚本
1. 打开PowerShell
2. 导航到项目目录:
   ```powershell
   cd c:\Users\Administrator\Desktop\JJ
   ```
3. 运行推送脚本:
   ```powershell
   .\easy_push.ps1
   ```

## 步骤3: 处理可能的认证问题
首次推送时，Git可能会提示您输入GitHub凭证:
- 对于GitHub用户名/密码认证: 输入您的GitHub用户名和密码
- 对于SSH认证: 确保已配置SSH密钥
- 对于个人访问令牌(PAT): 推荐使用此方式，可在GitHub的Settings > Developer settings > Personal access tokens创建

## 常见问题及解决方法
1. **Git未安装**
   - 下载并安装Git: https://git-scm.com/
   - 安装时确保选择"Add Git to PATH"

2. **远程仓库不存在**
   - 先在GitHub上创建仓库，然后更新脚本中的仓库URL

3. **权限不足**
   - 确保您对仓库有写入权限
   - 检查是否使用了正确的GitHub账号
   - 尝试创建个人访问令牌(PAT)并使用它进行认证

4. **推送失败，提示"fatal: refusing to merge unrelated histories"**
   - 这通常是因为本地仓库和远程仓库有不同的提交历史
   - 解决方案: 运行 `git pull origin main --allow-unrelated-histories`，然后再次尝试推送

5. **网络连接问题**
   - 检查您的网络连接
   - 如果使用代理，确保Git已配置代理

## 完成推送后
1. 登录GitHub，打开您的仓库，确认代码已成功推送
2. 在仓库的Settings > Secrets > Actions中添加必要的secrets（如FUND_API_KEY，如果需要）
3. 触发GitHub Actions工作流运行模型

如果您遇到其他问题，请参考GitHub官方文档或搜索相关错误信息。