# HTML 文档结构基础

## HTML 文档骨架

每个 HTML 页面都从一个标准的文档结构开始。`<!DOCTYPE html>` 声明告诉浏览器这是一个 HTML5 文档。`<html>` 标签是整个页面的根元素，包含 `lang` 属性来指定页面语言。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>我的网页</title>
</head>
<body>
    <h1>欢迎来到我的网站</h1>
    <p>这是一个段落。</p>
</body>
</html>
```

## 常见 HTML 标签

- `<h1>` 到 `<h6>`：标题标签，h1 最重要，h6 最次要
- `<p>`：段落标签，用于文本块
- `<a>`：超链接标签，`href` 属性指定目标 URL
- `<img>`：图片标签，`src` 属性指定图片路径，`alt` 属性提供替代文本
- `<div>`：块级容器，用于布局和分组
- `<span>`：行内容器，用于文本中的局部样式

## 语义化 HTML

HTML5 引入了语义化标签来让页面结构更有意义：`<header>`、`<footer>`、`<article>`、`<section>`、`<aside>`、`<nav>`。语义化标签不仅让代码更易读，还能帮助搜索引擎和屏幕阅读器理解页面结构。
