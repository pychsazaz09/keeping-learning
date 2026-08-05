# CSS 样式与布局入门

## CSS 是什么

CSS（层叠样式表，Cascading Style Sheets）用于控制 HTML 页面的视觉效果。它将内容和样式分离——HTML 管结构，CSS 管外观。一个 CSS 规则由选择器和声明块组成：

```css
h1 {
    color: blue;
    font-size: 24px;
    text-align: center;
}
```

## 三种引入 CSS 的方式

1. **内联样式**：直接写在 HTML 标签的 `style` 属性中（优先级最高，但不推荐大量使用）
2. **内部样式表**：写在 `<style>` 标签里，放在 `<head>` 中
3. **外部样式表**：单独的 `.css` 文件，通过 `<link>` 标签引入（最推荐，便于维护和缓存）

## CSS 选择器优先级（特异性）

选择器的优先级决定了当多个规则作用于同一个元素时，哪个规则生效：

- `!important` > 内联样式 > ID 选择器（`#id`）> 类选择器（`.class`）> 元素选择器（`div`）
- 当一个选择器包含多个部分时（如 `div.content .title`），每部分都会增加特异性

## Flexbox 布局基础

Flexbox 是 CSS3 引入的一维布局模型。核心概念：

- **容器属性**：`display: flex`、`justify-content`（主轴对齐）、`align-items`（交叉轴对齐）、`flex-direction`（主轴方向）
- **项目属性**：`flex-grow`（放大比例）、`flex-shrink`（缩小比例）、`flex-basis`（基础大小）

常见模式：`display: flex; justify-content: center; align-items: center` 实现水平垂直居中。

## Grid 布局基础

CSS Grid 是二维布局系统，比 Flexbox 更适合复杂的页面布局。通过 `grid-template-columns` 和 `grid-template-rows` 定义网格结构，使用 `gap` 设置间距。
