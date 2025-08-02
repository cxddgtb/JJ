# 基金短线买卖大模型 - 推送到GitHub脚本
# 此脚本将帮助您将项目代码推送到GitHub仓库

# 配置您的GitHub仓库信息
$githubRepoUrl = "https://github.com/您的用户名/您的仓库名.git"  # 替换为您的GitHub仓库URL
$branchName = "main"

# 检查Git是否已安装
try {
    git --version
    Write-Host "Git已安装，继续执行..."
} catch {
    Write-Host "错误: 未找到Git。请先安装Git并确保其在系统PATH中。"
    exit 1
}

# 初始化Git仓库（如果尚未初始化）
if (-not (Test-Path -Path ".git")) {
    Write-Host "初始化Git仓库..."
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: 初始化Git仓库失败。"
        exit 1
    }
}

# 添加远程仓库
Write-Host "添加远程仓库..."
$remoteExists = git remote | Select-String -Pattern "origin"
if (-not $remoteExists) {
    git remote add origin $githubRepoUrl
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: 添加远程仓库失败。请检查仓库URL是否正确。"
        exit 1
    }
} else {
    Write-Host "远程仓库已存在，更新URL..."
    git remote set-url origin $githubRepoUrl
    if ($LASTEXITCODE -ne 0) {
        Write-Host "错误: 更新远程仓库URL失败。"
        exit 1
    }
}

# 添加所有文件到暂存区
Write-Host "添加文件到暂存区..."
 git add .
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 添加文件失败。"
    exit 1
}

# 提交更改
Write-Host "提交更改..."
$commitMessage = "初始化基金短线买卖大模型项目"
git commit -m "$commitMessage"
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 提交更改失败。"
    exit 1
}

# 推送到GitHub
Write-Host "推送到GitHub..."
git push -u origin $branchName
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 推送失败。可能需要先在GitHub上创建仓库，或检查您的权限。"
    exit 1
}

Write-Host "成功: 代码已推送到GitHub仓库！"
Write-Host "接下来的步骤:"
Write-Host "1. 登录GitHub，打开您的仓库"
Write-Host "2. 在仓库的Settings > Secrets > Actions中添加FUND_API_KEY（如果需要）"
Write-Host "3. 触发GitHub Actions工作流运行"