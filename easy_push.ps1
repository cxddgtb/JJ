# 简易GitHub推送脚本
# 请确保已在GitHub上创建了仓库，并替换下面的仓库URL

# 配置GitHub仓库信息 (请替换为您自己的仓库信息)
$githubRepoUrl = "https://github.com/您的用户名/您的仓库名.git"
$yourName = "您的姓名"
$yourEmail = "您的邮箱@example.com"

# 检查是否已安装Git
try {
    git --version | Out-Null
    Write-Host "✓ Git已安装"
} catch {
    Write-Host "✗ 错误: 未找到Git。请先安装Git并确保其在系统PATH中。"
    exit 1
}

# 配置Git用户信息
Write-Host "配置Git用户信息..."
git config --global user.name "$yourName"
git config --global user.email "$yourEmail"
Write-Host "✓ Git用户信息已配置"

# 初始化Git仓库（如果尚未初始化）
if (-not (Test-Path -Path ".git")) {
    Write-Host "初始化Git仓库..."
    git init
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Git仓库已初始化"
    } else {
        Write-Host "✗ 错误: 初始化Git仓库失败。"
        exit 1
    }
} else {
    Write-Host "✓ Git仓库已存在"
}

# 添加远程仓库
Write-Host "添加远程仓库..."
$remoteExists = git remote | Select-String -Pattern "origin"
if (-not $remoteExists) {
    git remote add origin $githubRepoUrl
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 远程仓库已添加"
    } else {
        Write-Host "✗ 错误: 添加远程仓库失败。请检查仓库URL是否正确。"
        exit 1
    }
} else {
    Write-Host "✓ 远程仓库已存在，更新URL..."
    git remote set-url origin $githubRepoUrl
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 远程仓库URL已更新"
    } else {
        Write-Host "✗ 错误: 更新远程仓库URL失败。"
        exit 1
    }
}

# 添加所有文件到暂存区
Write-Host "添加文件到暂存区..."
git add .
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 文件已添加到暂存区"
} else {
    Write-Host "✗ 错误: 添加文件失败。"
    exit 1
}

# 提交更改
Write-Host "提交更改..."
$commitMessage = "更新基金短线买卖大模型代码"
git commit -m "$commitMessage"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 更改已提交"
} else {
    Write-Host "✗ 错误: 提交更改失败。可能没有需要提交的更改。"
    # 即使提交失败，也继续尝试推送
}

# 推送到GitHub
Write-Host "推送到GitHub..."
git push -u origin main
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 成功: 代码已推送到GitHub仓库！"
    Write-Host "
操作完成！您的代码已成功推送到GitHub。"
    Write-Host "接下来的步骤:"
    Write-Host "1. 登录GitHub，打开您的仓库"
    Write-Host "2. 在仓库的Settings > Secrets > Actions中添加必要的secrets"
    Write-Host "3. 触发GitHub Actions工作流运行"
} else {
    Write-Host "✗ 错误: 推送失败。常见原因及解决方法:"
    Write-Host "  - 仓库不存在: 请先在GitHub上创建仓库"
    Write-Host "  - 权限问题: 请确保您有权限访问该仓库"
    Write-Host "  - 网络问题: 请检查您的网络连接"
    Write-Host "  - 分支问题: 尝试使用 'git push -u origin HEAD' 推送当前分支"
    exit 1
}