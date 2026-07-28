"""Day 4 补课 — 可变对象陷阱 + @property/@staticmethod/@classmethod

阅读理解要点：
  Python 函数默认值在**定义时**创建一次，不是每次调用时创建
  def f(a=[]):  ← 这个 [] 在 import 时就创建了，之后每次调用指向同一个对象

  Java 里每次调用都是新的 → Java 没有这个坑

Pydantic 特殊规则：
  class QuestionCreate(BaseModel):
      tags: list[str] = []  ← Pydantic 安全！（Pydantic 内部做了特殊处理）
  普通函数：
      def f(tags=[]):       ← 陷阱！
"""

from dataclasses import dataclass

# ============================================================
# 1.3 可变对象默认参数陷阱
# ============================================================


# ❌ 陷阱版本
def add_tag_bad(name: str, tags: list = []):
    """BUG：每次调用共享同一个 list！"""
    tags.append(name)
    return tags


# ✅ 正确版本
def add_tag_good(name: str, tags: list | None = None):
    """正确：每次调用创建新 list"""
    if tags is None:
        tags = []
    tags.append(name)
    return tags


# 对比验证
def demo_mutable_trap():
    print("  [BUG] 陷阱版本:")
    print(f"    第一次: {add_tag_bad('Python')}")  # ['Python']
    print(f"    第二次: {add_tag_bad('生成器')}")  # ['Python', '生成器'] ← 共享了！

    print("  [OK]  正确版本:")
    print(f"    第一次: {add_tag_good('Python')}")  # ['Python']
    print(f"    第二次: {add_tag_good('生成器')}")  # ['生成器'] ← 独立！


# ============================================================
# 1.4 @property / @staticmethod / @classmethod
# ============================================================


@dataclass
class Question:
    """题目模型 — 演示三种装饰器"""

    title: str
    difficulty: str = "medium"
    _tags: list[str] | None = None

    # 类变量（所有实例共享，但不会被实例覆盖）
    DIFFICULTY_SCORE = {"easy": 1, "medium": 2, "hard": 3}

    # --- @property: 方法变身属性，访问不加括号 ---
    @property
    def difficulty_score(self) -> int:
        """计算难度分数 — 看起来像属性，实际是方法"""
        return self.DIFFICULTY_SCORE.get(self.difficulty, 0)

    @property
    def tags(self) -> list[str]:
        """tags 的 getter"""
        return self._tags or []

    @tags.setter
    def tags(self, value: list[str]):
        """tags 的 setter — 可以在赋值时加校验"""
        if len(value) > 10:
            raise ValueError("标签不能超过 10 个")
        self._tags = value

    # --- @staticmethod: 不访问 self/cls，纯粹的工具函数 ---
    @staticmethod
    def is_valid_title(title: str) -> bool:
        """校验标题长度（不需要访问实例）"""
        return 2 <= len(title) <= 500

    # --- @classmethod: 接收类本身，做工厂方法 ---
    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        """工厂方法：从字典创建 Question"""
        return cls(
            title=data["title"],
            difficulty=data.get("difficulty", "medium"),
            _tags=data.get("tags", []),
        )

    @classmethod
    def easy(cls, title: str) -> "Question":
        """快捷工厂：创建一道简单题"""
        return cls(title=title, difficulty="easy")


# ============================================================
# 验证入口
# ============================================================
def main():
    print("=" * 50)
    print("1.3 可变对象默认参数陷阱")
    print("=" * 50)
    demo_mutable_trap()

    print()
    print("=" * 50)
    print("1.4 @property / @staticmethod / @classmethod")
    print("=" * 50)

    # @classmethod 工厂
    q = Question.from_dict({"title": "什么是 Python GIL？", "difficulty": "hard"})
    q.tags = ["Python", "并发"]

    # @property 读
    print(f"  标题: {q.title}")
    print(f"  难度: {q.difficulty}")
    print(f"  难度分数: {q.difficulty_score}")  # ← 不加括号！
    print(f"  标签: {q.tags}")

    # @staticmethod 工具
    print(f"  标题校验: {Question.is_valid_title('A')}")  # False（太短）
    print(f"  标题校验: {Question.is_valid_title(q.title)}")  # True

    # @classmethod 快捷工厂
    easy_q = Question.easy("什么是 list 和 tuple 的区别？")
    print(f"  快捷创建: [{easy_q.difficulty}] {easy_q.title}")

    # @tags.setter 校验
    try:
        q.tags = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]  # 11 个
    except ValueError as e:
        print(f"  setter 校验生效: {e}")


if __name__ == "__main__":
    main()
