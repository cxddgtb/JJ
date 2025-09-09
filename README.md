# 代理节点爬取与Clash订阅生成

此项目自动爬取全网代理节点，筛选出速度最快的100个有效节点，并生成Clash订阅配置。

## 功能特点

- 自动爬取全网代理节点
- 测试节点速度并筛选最快的100个有效节点
- 生成包含完整分流策略的Clash订阅配置
- 定期更新订阅内容，保持最新策略
- 单文件更新，不产生多余文件

## 使用方法

1. Fork此仓库到您的GitHub账户
2. 在仓库设置中添加名为`REPO_ACCESS_TOKEN`的Secret，值为您GitHub的个人访问令牌
3. 工作流将自动运行，生成的订阅文件将更新到仓库的`subscription.yml`中

## 订阅地址

订阅地址为：`https://raw.githubusercontent.com/您的用户名/proxy-scraper-clash/main/subscription.yml`

## 注意事项

- 请确保您的GitHub令牌具有仓库读写权限
- 工作流每天自动运行一次，也可手动触发
- 生成的订阅文件会覆盖旧版本，始终只保留最新版本
