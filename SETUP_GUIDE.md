# 独立内容仓库设置指南

你的博客已配置为使用独立的内容仓库模式。

## 架构说明

- **博客仓库（当前）**: 包含配置、主题、生成脚本
- **内容仓库**: 只包含 Markdown 文章（md 目录）
- **自动部署**: 内容仓库更新后，博客会自动重新生成和部署

## 配置步骤

### 1. 生成 SSH Deploy Key

在终端运行：

```bash
ssh-keygen -t ed25519 -C "blog-content-access" -f content_deploy_key -N ""
```

这会生成两个文件：
- `content_deploy_key` (私钥)
- `content_deploy_key.pub` (公钥)

### 2. 配置内容仓库

1. 打开你的内容仓库: git@github.com:soft98-top/blog.git
2. 进入 Settings → Deploy keys
3. 点击 "Add deploy key"
4. 标题填写: "Blog Access"
5. 将 `content_deploy_key.pub` 的内容粘贴到 Key 框中
6. **不要勾选** "Allow write access"（只需要读权限）
7. 点击 "Add key"

### 3. 配置博客仓库 Secrets

1. 打开当前博客仓库的 GitHub 页面
2. 进入 Settings → Secrets and variables → Actions
3. 添加以下 secrets：

   **CONTENT_REPO_KEY**:
   - 点击 "New repository secret"
   - Name: `CONTENT_REPO_KEY`
   - Value: 将 `content_deploy_key` (私钥) 的完整内容粘贴进去
   - 点击 "Add secret"

   **CONTENT_REPO_URL**:
   - 点击 "New repository secret"
   - Name: `CONTENT_REPO_URL`
   - Value: `git@github.com:soft98-top/blog.git`
   - 点击 "Add secret"

### 4. 配置 GitHub Pages

1. 进入 Settings → Pages
2. Source 选择 "GitHub Actions"

### 5. 推送代码

```bash
cd myblog
git add .
git commit -m "Initial blog setup with separate content repo"
git remote add origin <你的博客仓库URL>
git push -u origin main
```

### 6. 测试自动部署

1. 在内容仓库中添加或修改 Markdown 文件
2. 提交并推送到 main 分支
3. 等待最多 30 分钟（或手动触发 workflow）
4. 博客会自动更新

## 手动触发部署

如果不想等待定时任务，可以手动触发：

1. 进入博客仓库的 Actions 页面
2. 选择 "Deploy Blog" workflow
3. 点击 "Run workflow"

## 本地开发

本地开发时，需要手动克隆内容仓库：

```bash
cd myblog
git clone git@github.com:soft98-top/blog.git md
python gen.py
```

生成的静态文件在 `public/` 目录中。

## 工作流程

1. 在内容仓库中编写文章
2. 提交并推送
3. GitHub Actions 自动检测更新
4. 自动生成静态网站
5. 自动部署到 GitHub Pages

## 安全说明

- Deploy Key 只有读取内容仓库的权限
- 私钥安全存储在 GitHub Secrets 中
- 内容仓库不需要知道博客仓库的存在
- 可以为不同的人分配不同的仓库权限

## 故障排查

如果部署失败，检查：

1. Secrets 是否正确配置
2. Deploy Key 是否正确添加到内容仓库
3. 内容仓库 URL 是否正确（必须是 SSH 格式）
4. GitHub Actions 的日志输出

---

配置完成后，删除 `content_deploy_key` 和 `content_deploy_key.pub` 文件以确保安全。
