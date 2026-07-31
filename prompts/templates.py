
Generate_Question_Prompts='''你是一位资深 {topic} 面试官,
要求：
1. 生成 {count} 道 {difficulty} 难度的面试题
2. 每题包含：title（题目标题）、tags（逗号分隔的标签）、answer（参考答案100-300字）
3. 题目要有区分度，考察理解和应用，不是简单的"XX是什么"

请严格用 JSON 数组格式返回，不要加任何额外文字：
[
{{"title": "...", "tags": "xxx,yyy", "answer": "..."}},
...
]'''
