# Python数据分析完整学习指南

> 一份涵盖Python数据分析全技术栈的系统性学习文档，包含基础语法、NumPy、Pandas、可视化、数据清洗、统计分析、机器学习及实战案例。

---

## 目录

- [第1章 Python基础语法与数据结构](#第1章-python基础语法与数据结构)
- [第2章 NumPy数值计算](#第2章-numpy数值计算)
- [第3章 Pandas数据处理与分析](#第3章-pandas数据处理与分析)
- [第4章 Matplotlib与Seaborn数据可视化](#第4章-matplotlib与seaborn数据可视化)
- [第5章 数据清洗与预处理技术](#第5章-数据清洗与预处理技术)
- [第6章 探索性数据分析与统计分析](#第6章-探索性数据分析与统计分析)
- [第7章 机器学习入门（面向数据分析）](#第7章-机器学习入门面向数据分析)
- [第8章 实战案例分析](#第8章-实战案例分析)
- [第9章 高性能计算与大数据处理](#第9章-高性能计算与大数据处理)
- [第10章 时间序列分析与预测](#第10章-时间序列分析与预测)
- [第11章 因果推断](#第11章-因果推断)
- [第12章 数据质量与验证体系](#第12章-数据质量与验证体系)
- [第13章 MLOps与实验管理](#第13章-mlops与实验管理)
- [第14章 可组合数据栈与未来趋势](#第14章-可组合数据栈与未来趋势)

---

## 第1章 Python基础语法与数据结构

### 1.1 环境搭建

Python数据分析推荐使用Anaconda发行版，它预装了NumPy、Pandas、Matplotlib、Jupyter等核心工具。

```bash
# 安装常用数据分析库
pip install numpy pandas matplotlib seaborn scipy scikit-learn jupyter
```

验证安装：

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

print(f"NumPy: {np.__version__}")
print(f"Pandas: {pd.__version__}")
print(f"Seaborn: {sns.__version__}")
```

### 1.2 变量与基本数据类型

Python是**动态类型语言**，变量在使用前不需要声明类型。Python内置六种标准数据类型：

| 数据类型 | 说明 | 示例 |
|---------|------|------|
| `int` | 整数，无大小限制 | `42`, `-7`, `0xff` |
| `float` | 浮点数（双精度） | `3.14`, `-0.5`, `1.6e-19` |
| `complex` | 复数 | `3 + 4j` |
| `str` | 字符串（不可变） | `"数据分析"`, `'hello'` |
| `bool` | 布尔值 | `True`, `False` |
| `NoneType` | 空值 | `None` |

```python
# 多变量同时赋值
x, y, z = 10, 3.14, "Python"

# 类型检查与转换
print(type(x))        # <class 'int'>
print(isinstance(y, float))  # True

# 类型转换
int("42")      # 42
float(42)      # 42.0
str(3.14)      # "3.14"
bool(0)         # False; 非零值为True
```

### 1.3 字符串操作

字符串在数据处理中无处不在——列名处理、文本清洗、正则匹配都离不开它。

```python
# 字符串格式化（三种方式）
name, age = "张三", 30

# f-string（Python 3.6+，推荐）
s1 = f"{name}今年{age}岁"

# format方法
s2 = "{}今年{}岁".format(name, age)

# %格式化（旧式）
s3 = "%s今年%d岁" % (name, age)

# 常用字符串方法
"  hello world  ".strip()          # "hello world"（去除两端空格）
"python".upper()                    # "PYTHON"
"DATA".lower()                      # "data"
"hello world".split()               # ["hello", "world"]
",".join(["a", "b", "c"])           # "a,b,c"
"hello".replace("l", "x")           # "hexxo"
"apple,banana".find("banana")       # 6（子串起始位置）
"data.csv".endswith(".csv")         # True
"sales_2024".startswith("sales")    # True

# 字符串切片
s = "Python数据分析"
s[0:6]     # "Python"
s[6:]      # "数据分析"
s[::-1]    # "析分据数nohtyP"（反转）

# 多行字符串
query = """
SELECT name, SUM(sales) AS total
FROM orders
WHERE year = 2024
GROUP BY name
"""
```

### 1.4 列表（List）—— 最核心的可变序列

列表是数据分析中使用频率最高的数据结构，支持异构元素、动态扩容。

```python
# 创建列表
numbers = [1, 2, 3, 4, 5]
mixed = [1, "hello", 3.14, True, [1, 2]]   # 可容纳任意类型

# 索引：Python索引从0开始，支持负索引
numbers[0]       # 1（第一个）
numbers[-1]      # 5（最后一个）
numbers[-2]      # 4（倒数第二个）

# 切片：list[start:stop:step]，左闭右开
numbers[1:4]     # [2, 3, 4]
numbers[::2]     # [1, 3, 5]（步长为2）
numbers[::-1]    # [5, 4, 3, 2, 1]（反转）

# 修改元素
numbers[0] = 100
numbers[1:3] = [20, 30]     # 切片赋值

# 列表方法详解
numbers.append(6)            # 末尾追加一个元素
numbers.extend([7, 8, 9])    # 末尾追加多个元素
numbers.insert(0, 0)         # 在索引0处插入0
numbers.remove(3)            # 删除第一个值为3的元素
del numbers[0]               # 按索引删除
popped = numbers.pop()       # 弹出末尾元素并返回
popped = numbers.pop(2)      # 弹出索引2处的元素
index = numbers.index(5)     # 查找值5的索引（不存在会抛出ValueError）
count = numbers.count(3)     # 统计值3的出现次数
numbers.sort()               # 原地升序排序
numbers.sort(reverse=True)   # 原地降序排序
sorted_list = sorted(numbers) # 返回新排序列表，原列表不变
numbers.reverse()            # 原地反转

# 列表推导式（List Comprehension）—— Python的标志性特性
# 语法：[表达式 for 变量 in 可迭代对象 if 条件]
squares = [x**2 for x in range(10)]                 # [0,1,4,9,16,25,36,49,64,81]
evens = [x for x in range(20) if x % 2 == 0]        # 过滤
pairs = [(x, y) for x in range(3) for y in range(3)] # 嵌套循环

# 列表推导式与map/filter的等价关系
list(map(str, [1, 2, 3]))            # 等价于 [str(x) for x in [1,2,3]]
list(filter(lambda x: x>0, [-1,0,1])) # 等价于 [x for x in [-1,0,1] if x>0]
```

**应用场景**：存储数据行列表、收集分析结果、构建特征列表、处理文件行。

### 1.5 元组（Tuple）—— 不可变序列

元组创建后不可修改，适合表示固定集合、函数多返回值、字典键。

```python
# 创建元组
point = (3, 4)
single = (1,)        # 单元素元组：逗号不可省略！
empty = ()

# 元组解包（Unpacking）
x, y = point         # x=3, y=4
a, *rest = (1, 2, 3, 4)  # a=1, rest=[2,3,4]

# 命名元组：兼具元组的不可变性和对象的可读性
from collections import namedtuple
Record = namedtuple('Record', ['name', 'age', 'city'])
r = Record('张三', 30, '北京')
print(r.name, r.age)   # 张三 30
```

### 1.6 字典（Dictionary）—— 键值对映射

字典是Pandas DataFrame的底层灵感来源，在数据分析中用于映射表、配置、统计计数。

```python
# 创建字典
person = {'name': '张三', 'age': 30, 'city': '北京'}
data = dict(name='李四', age=25)           # 关键字方式
kv_pairs = dict([('a', 1), ('b', 2)])      # 从序列创建

# 访问键值
person['name']           # 直接访问（键不存在时报KeyError）
person.get('salary', 0)  # 安全访问（键不存在返回默认值0）

# 修改与新增
person['age'] = 31       # 修改已有键
person['job'] = '分析师'  # 新增键值对
person.update({'age': 32, 'email': 'test@example.com'})  # 批量更新

# 删除
del person['job']
age = person.pop('age')
person.pop('salary', None)      # 安全删除
person.popitem()                 # 删除最后一个（3.7+）
person.clear()                   # 清空字典

# 遍历
for key in person: pass                  # 遍历键
for key, value in person.items(): pass   # 遍历键值对
for value in person.values(): pass       # 遍历值

# 字典推导式
word_freq = {word: len(word) for word in ['apple', 'banana', 'cherry']}
```

**应用场景**：DataFrame列映射、分类标签编码表、配置参数、JSON数据处理。

### 1.7 集合（Set）—— 无序不重复元素集

集合用于去重、成员关系测试、数学集合运算（交集、并集、差集）。

```python
# 创建集合
A = {1, 2, 3, 4, 5}
B = {4, 5, 6, 7, 8}
empty_set = set()    # 空集合（注意：{}创建的是空字典）

# 集合运算
A | B         # 并集: {1,2,3,4,5,6,7,8}
A & B         # 交集: {4,5}
A - B         # 差集: {1,2,3}
A ^ B         # 对称差集: {1,2,3,6,7,8}

# 集合方法
A.add(6)              # 添加元素
A.remove(6)           # 移除（不存在则报错）
A.discard(10)         # 安全移除
A.update([7, 8])      # 批量添加

# 集合推导式
squares = {x**2 for x in range(-5, 5)}
```

**应用场景**：DataFrame列唯一值获取、用户ID交集分析、数据去重。

### 1.8 控制流程

```python
# 条件语句
score = 85
if score >= 90:
    grade = 'A'
elif score >= 80:
    grade = 'B'
elif score >= 70:
    grade = 'C'
else:
    grade = 'D'

# 单行条件表达式
status = "合格" if score >= 60 else "不合格"

# for循环：遍历任何可迭代对象
df_columns = ['name', 'age', 'salary']
for col in df_columns:
    print(f"处理列: {col}")

# enumerate：同时获取索引和值
for i, col in enumerate(df_columns):
    print(f"第{i}列: {col}")

# zip：并行遍历多个序列
for col, dtype in zip(df_columns, ['str', 'int', 'float']):
    print(f"{col}: {dtype}")

# while循环：条件驱动
total, i = 0, 1
while i <= 100:
    total += i
    i += 1

# break/continue/else
for x in range(10):
    if x == 3: continue   # 跳过本次
    if x == 7: break      # 终止循环
    print(x)
else:
    print("循环正常结束（未遇到break）")

# pass：占位符
def future_function():
    pass
```

### 1.9 异常处理

数据分析中数据质量不可控，异常处理是代码健壮性的保障。

```python
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        print("除数不能为零")
        return float('nan')
    except TypeError:
        print("类型错误，请传入数值")
        return None
    finally:
        print("计算完成")

# 处理DataFrame操作中的异常
import pandas as pd

try:
    df = pd.read_csv('data.csv')
    result = df['price'].mean()
except FileNotFoundError:
    print("数据文件不存在")
except KeyError:
    print("DataFrame中没有'price'列")
except Exception as e:
    print(f"未知错误: {e}")
finally:
    print("数据读取流程结束")
```

### 1.10 函数

```python
# 基本函数定义
def calculate_growth(current, previous):
    """计算增长率"""
    if previous == 0:
        return float('inf')
    return (current - previous) / previous

print(f"增长率: {calculate_growth(120, 100):.1%}")

# 多返回值
def describe_series(data):
    """返回多个统计量"""
    import numpy as np
    return np.mean(data), np.std(data), np.median(data)

mean, std, median = describe_series([1, 2, 3, 4, 5])

# *args 和 **kwargs
def flexible_agg(data, *funcs, **options):
    """灵活聚合：接受任意多个函数和选项"""
    result = {}
    for func in funcs:
        result[func.__name__] = func(data)
    if options.get('round', False):
        result = {k: round(v, 2) for k, v in result.items()}
    return result

import numpy as np
result = flexible_agg([1, 2, 3, 4, 5], np.mean, np.sum, np.std, round=True)
print(result)  # {'mean': 3.0, 'sum': 15, 'std': 1.41}

# 匿名函数 lambda
add = lambda x, y: x + y
square = lambda x: x ** 2

# lambda在数据分析中的典型用法
df_list = [
    {'name': '张三', 'score': 85},
    {'name': '李四', 'score': 92},
    {'name': '王五', 'score': 78}
]
sorted_df = sorted(df_list, key=lambda x: x['score'], reverse=True)
```

### 1.11 生成器与迭代器

大数据集的内存优化策略。

```python
# 生成器函数
def chunk_reader(file_path, chunk_size=1000):
    """分块读取大文件"""
    chunk = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            chunk.append(line.strip())
            if (i + 1) % chunk_size == 0:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

# 生成器表达式
# 对比：列表推导式一次性创建100万个元素的列表
# squares = [x**2 for x in range(1000000)]  # 内存占用大
gen = (x**2 for x in range(1000000))       # 惰性求值，内存占用极小

# 迭代器协议
# 将可迭代对象转为迭代器
it = iter([1, 2, 3])
next(it)   # 1
next(it)   # 2
next(it)   # 3
# next(it) # StopIteration
```

### 1.12 文件与路径操作

```python
import os
import glob

# 文件读写
with open('data.txt', 'r', encoding='utf-8') as f:
    content = f.read()

with open('output.txt', 'w', encoding='utf-8') as f:
    f.write("数据分析结果\n")

# 路径操作
os.path.exists('data.xlsx')             # 判断文件是否存在
os.path.join('data', '2024', 'sales.csv') # 安全拼接路径
os.path.dirname('/path/to/file.csv')      # 目录部分

# 批量文件匹配
csv_files = glob.glob('data/**/*.csv', recursive=True)
```

---

## 第2章 NumPy数值计算

### 2.1 概述与核心优势

NumPy（Numerical Python）是整个Python数据科学生态的基石。Pandas、scikit-learn、SciPy都构建在NumPy之上。

**核心优势**：
- **向量化运算**：避免Python层级的for循环，运算速度提升10-100倍
- **广播机制**：自动扩展不同形状数组以进行元素级运算
- **内存效率**：ndarray使用连续内存块，比Python列表节省空间
- **丰富的数学函数**：线性代数、傅里叶变换、随机数生成

```python
import numpy as np

# 性能对比：向量化 vs Python循环
arr = np.arange(1, 1000001)

# 向量化（极快）
%timeit result = arr * 2 + 1

# Python循环（慢）
%timeit result = [x * 2 + 1 for x in range(1, 1000001)]
```

### 2.2 ndarray创建与属性

ndarray（N-dimensional array）是NumPy的核心数据结构。

```python
import numpy as np

# ---- 从Python数据结构创建 ----
arr1 = np.array([1, 2, 3, 4, 5])           # 从列表
arr2 = np.array([[1, 2], [3, 4], [5, 6]])  # 二维
arr3 = np.array([1, 2, 3], dtype='float32')# 指定数据类型

# ---- 创建函数 ----
np.zeros(5)                # [0. 0. 0. 0. 0.]
np.zeros((3, 4))           # 3行4列全零矩阵
np.ones((2, 3))            # 全1数组
np.full((3, 3), 3.14)      # 填充指定值
np.eye(4)                  # 4x4单位矩阵
np.diag([1, 2, 3, 4])      # 对角矩阵

# ---- 序列数组 ----
np.arange(0, 10, 2)        # [0 2 4 6 8]，指定步长
np.linspace(0, 1, 5)       # [0. 0.25 0.5 0.75 1.]，指定元素个数
np.logspace(0, 3, 4)       # [1. 10. 100. 1000.]，等比数列
np.geomspace(1, 1000, 4)   # [1. 10. 100. 1000.]（同上）

# ---- ndarray关键属性 ----
arr = np.arange(24).reshape(2, 3, 4)
arr.ndim      # 3（维度数量）
arr.shape     # (2, 3, 4)（各维度大小）
arr.dtype     # dtype('int64')（元素数据类型）
arr.size      # 24（元素总数）
arr.itemsize  # 8（每个元素字节数）
arr.nbytes    # 192（总字节数 = size × itemsize）
```

### 2.3 多维数组索引与切片

```python
arr = np.arange(24).reshape(4, 6)
print(arr)
# [[ 0  1  2  3  4  5]
#  [ 6  7  8  9 10 11]
#  [12 13 14 15 16 17]
#  [18 19 20 21 22 23]]

# ---- 基本索引 ----
arr[0, 0]      # 0（单个元素）
arr[2, 3]      # 15
arr[-1, -1]    # 23（负索引）

# ---- 切片 ----
arr[0:2]       # 第0-1行
arr[0:2, 1:4]  # 第0-1行，第1-3列
arr[:, 0]      # 所有行，第0列 → [0, 6, 12, 18]
arr[::2, ::3]  # 隔行隔列采样

# ---- 布尔索引（条件筛选）----
mask = arr > 10
arr[mask]      # [11 12 13 14 15 16 17 18 19 20 21 22 23]

# 组合条件
arr[(arr > 10) & (arr < 20)]  # 10-20之间
arr[(arr < 5) | (arr > 20)]   # <5 或 >20

# 条件赋值
arr[arr > 10] = -1             # 将所有>10的元素设为-1

# ---- 花式索引（Fancy Indexing）----
arr[[0, 2, 3]]                    # 选取第0,2,3行
arr[[0, 2], [1, 3]]               # 取arr[0,1]和arr[2,3]
arr[:, [0, -1]]                   # 所有行，第0列和最后一列

# ---- Where函数（条件选择）----
result = np.where(arr > 10, arr, 0)  # >10保留，否则0
result = np.where(arr > 10, 1, -1)   # >10为1，否则-1
```

### 2.4 数组形状变换

```python
arr = np.arange(12)

# reshape：改变形状（元素总数必须不变）
arr.reshape(3, 4)         # 变为3x4
arr.reshape(3, -1)        # -1表示自动推断该维度
arr.reshape(2, 2, 3)      # 变为2x2x3

# ravel：展平为1D（返回视图，可能共享内存）
flat_view = arr.ravel()

# flatten：展平为1D（始终返回副本）
flat_copy = arr.flatten()

# 转置
arr.reshape(3, 4).T       # 使用.T属性转置
arr.reshape(3, 4).transpose()  # 等价

# resize：原地改变形状
arr.resize(3, 4)

# swapaxes：交换两个轴
arr_3d = np.arange(24).reshape(2, 3, 4)
arr_3d.swapaxes(0, 1)     # 交换第0和第1轴

# newaxis：增加维度
arr_1d = np.arange(5)
row = arr_1d[np.newaxis, :]   # (1, 5) 行向量
col = arr_1d[:, np.newaxis]    # (5, 1) 列向量

# squeeze：去除长度为1的维度
arr_singleton = np.array([[[1, 2, 3]]])  # shape (1, 1, 3)
arr_singleton.squeeze()                   # shape (3,)
```

### 2.5 数组拼接与分割

```python
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])

# ---- 拼接 ----
np.concatenate([a, b])                    # [1 2 3 4 5 6]

A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])
np.concatenate([A, B], axis=0)            # 竖直拼接
np.concatenate([A, B], axis=1)            # 水平拼接

np.vstack([A, B])          # 等价于 axis=0 拼接
np.hstack([A, B])          # 等价于 axis=1 拼接
np.dstack([A, B])          # 深度拼接（新增第三维）

np.column_stack([a, b])    # 转为列后拼接 [[1 4] [2 5] [3 6]]
np.row_stack([a, b])       # 转为行后拼接 [[1 2 3] [4 5 6]]

# ---- 分割 ----
arr = np.arange(9)
np.split(arr, 3)                      # 等分为3份
np.split(arr, [2, 5])                 # 按位置[0:2], [2:5], [5:]分割

arr_2d = np.arange(16).reshape(4, 4)
np.vsplit(arr_2d, 2)                  # 垂直分割
np.hsplit(arr_2d, 2)                  # 水平分割
```

### 2.6 向量化运算

NumPy的核心威力在于**向量化运算**——所有运算直接作用于整个数组。

```python
arr = np.array([1, 2, 3, 4, 5])

# 算术运算（逐元素）
arr + 10         # [11 12 13 14 15]
arr * 2          # [2 4 6 8 10]
arr ** 2         # [1 4 9 16 25]
arr % 2          # [1 0 1 0 1]

# 比较运算（返回布尔数组）
arr > 2          # [False False True True True]

# 逻辑运算
np.logical_and(arr > 1, arr < 5)  # 组合条件
np.any(arr > 3)                    # 是否存在>3的元素
np.all(arr > 0)                    # 是否全部>0
np.isclose(0.1 + 0.2, 0.3)        # 浮点数近似相等

# 数学函数（全部逐元素）
np.sqrt(arr)     # 平方根
np.exp(arr)      # e^x
np.log(arr)      # 自然对数
np.log10(arr)    # 以10为底对数
np.sin(arr)      # 三角函数
np.abs(arr)      # 绝对值
np.round(arr, 2) # 四舍五入
np.clip(arr, 2, 4)  # 截断到[2,4]范围

# 统计函数
arr = np.array([1, 2, 3, 4, 5])
np.sum(arr)          # 15
np.mean(arr)         # 3.0
np.std(arr)          # 1.414（总体标准差）
np.std(arr, ddof=1)  # 1.581（样本标准差）
np.var(arr)          # 2.0（方差）
np.min(arr)          # 1
np.max(arr)          # 5
np.argmin(arr)       # 0（最小值的索引位置）
np.argmax(arr)       # 4（最大值的索引位置）
np.median(arr)       # 3.0（中位数）
np.percentile(arr, 25)  # 2.0（25分位数）
np.quantile(arr, 0.75)  # 4.0（75分位数）
np.cumsum(arr)       # [1 3 6 10 15]（累计和）
np.cumprod(arr)      # [1 2 6 24 120]（累计积）
np.diff(arr)         # [1 1 1 1]（差分）

# 轴参数（axis）：沿指定轴计算
arr_2d = np.arange(12).reshape(3, 4)
np.sum(arr_2d, axis=0)   # [12 15 18 21]（沿行方向，每列求和）
np.sum(arr_2d, axis=1)   # [6 22 38]（沿列方向，每行求和）

# 排序
np.sort(arr)              # 返回排序副本
arr.sort()                # 原地排序
np.argsort(arr)           # 返回排序后的索引
top_3_idx = np.argpartition(arr, -3)[-3:]  # 效率更高的top k索引
```

### 2.7 广播机制（Broadcasting）

广播是NumPy处理不同形状数组运算的规则，避免了不必要的复制。

**广播规则**：从尾端维度开始比较，满足以下条件之一即可广播：
1. 两个维度相等
2. 其中一个维度为1

```python
# 标量与数组
arr = np.arange(5)     # shape (5,)
arr + 10               # 10被广播到所有元素

# 一维与二维
A = np.arange(3)[:, np.newaxis]   # shape (3,1)
B = np.arange(4)                   # shape (4,)
result = A + B                     # shape (3,4)，自动广播
print(result)
# [[0 1 2 3]
#  [1 2 3 4]
#  [2 3 4 5]]

# 数据分析中的实际应用：中心化
data = np.random.randn(100, 5)     # 100行5列的样本数据
centered = data - data.mean(axis=0)  # 每列减去各自的均值
standardized = centered / data.std(axis=0)  # Z-score标准化
```

### 2.8 线性代数

```python
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

# 矩阵乘法
A @ B                        # Python 3.5+ 的矩阵乘运算符
np.dot(A, B)                 # 等价
np.matmul(A, B)              # 等价

# 向量内积/外积
v1, v2 = np.array([1, 2, 3]), np.array([4, 5, 6])
np.dot(v1, v2)               # 32（内积/点积）
np.outer(v1, v2)             # 外积

# ---- np.linalg 模块 ----
np.linalg.inv(A)             # 逆矩阵
np.linalg.det(A)             # 行列式
np.linalg.eig(A)             # 特征值与特征向量
np.linalg.svd(A)             # 奇异值分解（SVD）
np.linalg.norm(A)            # 矩阵范数（默认Frobenius）
np.linalg.norm(v1, ord=2)    # 向量L2范数（欧氏距离）
np.linalg.norm(v1, ord=1)    # L1范数
np.linalg.matrix_rank(A)     # 矩阵的秩
np.linalg.solve(A, b)        # 解线性方程组 Ax = b
np.linalg.lstsq(A, b)        # 最小二乘解
```

**应用场景**：主成分分析（PCA）的协方差矩阵特征分解、线性回归的正规方程求解、距离计算。

### 2.9 随机数生成

数据分析中的随机数用于：采样、模拟、交叉验证分割、数据增强。

```python
np.random.seed(42)   # 固定随机种子（保证可复现）

# 基本随机数
np.random.rand(3, 4)                    # [0,1)均匀分布
np.random.randn(100)                    # 标准正态分布
np.random.randint(0, 100, (3, 5))       # 指定范围的整数

# 参数化分布
np.random.normal(loc=0, scale=1, size=100)     # 正态分布
np.random.uniform(low=0, high=10, size=100)     # 均匀分布
np.random.exponential(scale=1.0, size=100)      # 指数分布
np.random.poisson(lam=3, size=100)              # 泊松分布
np.random.binomial(n=10, p=0.5, size=100)       # 二项分布
np.random.gamma(shape=2, scale=2, size=100)     # 伽马分布
np.random.beta(a=2, b=5, size=100)              # Beta分布
np.random.chisquare(df=2, size=100)             # 卡方分布

# 随机采样
arr = np.arange(100)
sample = np.random.choice(arr, size=10, replace=False)  # 不放回抽样
bootstrap = np.random.choice(arr, size=100, replace=True)  # 有放回（Bootstrap）

# 打乱顺序
np.random.shuffle(arr)               # 原地打乱
permuted = np.random.permutation(arr) # 返回新数组

# 随机种子上下文
np.random.seed(42)         # 全局设置
rng = np.random.default_rng(42)  # 推荐：独立生成器（NumPy 1.17+）
rng.normal(0, 1, 10)
```

---

## 第3章 Pandas数据处理与分析

### 3.1 核心数据结构

Pandas提供两种核心数据结构：

- **Series**：带标签的一维数组，类似"带索引的NumPy数组"
- **DataFrame**：带标签的二维表格，类似"关系数据库表或Excel工作表"

```python
import pandas as pd
import numpy as np

# ---- Series ----
s = pd.Series([1, 3, 5, np.nan, 9])
print(s)
# 0    1.0
# 1    3.0
# 2    5.0
# 3    NaN
# 4    9.0
# dtype: float64

# 自定义索引
s = pd.Series([100, 200, 300], index=['a', 'b', 'c'], name='revenue')
print(s['b'])   # 200

# 从字典创建
population = pd.Series({
    '北京': 2154, '上海': 2487, '广州': 1867, '深圳': 1756
})

# ---- DataFrame ----
# 从字典创建（最常用）
df = pd.DataFrame({
    '姓名': ['张三', '李四', '王五', '赵六'],
    '年龄': [25, 30, 35, 28],
    '薪资': [5000, 8000, 7500, 6000],
    '部门': ['技术', '市场', '技术', '运营'],
    '入职日期': pd.to_datetime(['2020-01-15', '2019-06-01', '2021-03-12', '2018-11-20'])
})
print(df)

# 从列表创建
df = pd.DataFrame([
    {'name': 'Alice', 'score': 85},
    {'name': 'Bob', 'score': 92},
    {'name': 'Charlie', 'score': 78}
])

# 从NumPy数组创建
data = np.random.randn(5, 3)
columns = ['A', 'B', 'C']
df = pd.DataFrame(data, columns=columns)

# DataFrame属性
df.shape        # (4, 5)  行数,列数
df.dtypes       # 每列的数据类型
df.axes         # [行索引, 列索引]
df.values       # 转为NumPy数组
df.columns      # 列名
df.index        # 行索引
```

### 3.2 数据读取（IO操作）

Pandas支持从CSV、Excel、SQL、JSON、HTML、Parquet、HDF5等格式读取数据。

```python
# ---- 读取CSV ----
df = pd.read_csv('data.csv')
df = pd.read_csv('data.csv', sep='\t', encoding='gbk')           # TSV文件
df = pd.read_csv('data.csv', usecols=['name', 'age', 'salary'])  # 只读指定列
df = pd.read_csv('data.csv', dtype={'age': 'int32', 'id': 'str'})# 指定列类型
df = pd.read_csv('data.csv', parse_dates=['date'])               # 自动解析日期

# 日期解析
df = pd.read_csv('data.csv', parse_dates={'timestamp': ['date', 'time']})
df = pd.read_csv('data.csv', date_parser=lambda x: pd.to_datetime(x, format='%Y%m%d'))

# 分块读取（处理超大文件）
chunk_iter = pd.read_csv('large_file.csv', chunksize=10000)
for chunk in chunk_iter:
    # 对每块数据做处理
    processed = chunk.groupby('category').sum()

# ---- 读取Excel ----
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')
df = pd.read_excel('data.xlsx', sheet_name=0)           # 按位置
dfs = pd.read_excel('data.xlsx', sheet_name=None)       # 读取所有sheet，返回字典

# ---- 读取JSON ----
df = pd.read_json('data.json')
df = pd.read_json('data.json', orient='records', lines=True)  # 每行一个JSON对象

# ---- 从数据库读取 ----
from sqlalchemy import create_engine
engine = create_engine('sqlite:///database.db')
df = pd.read_sql('SELECT * FROM orders WHERE year=2024', engine)

# ---- 写入数据 ----
df.to_csv('output.csv', index=False, encoding='utf-8-sig')  # Excel兼容中文
df.to_excel('output.xlsx', sheet_name='结果', index=False)
df.to_json('output.json', orient='records', force_ascii=False)
df.to_parquet('output.parquet', index=False)                # 高效列式存储
df.to_sql('table_name', engine, if_exists='replace', index=False)
```

### 3.3 数据探查

拿到数据的第一步永远是"看"——理解数据结构、类型、缺失情况。

```python
df.head(10)              # 前10行
df.tail(5)               # 最后5行
df.sample(5)             # 随机5行
df.info()                # 数据类型、非空数量、内存占用
df.describe()            # 数值列的八大统计量
df.describe(include='all')            # 包含所有列类型
df.describe(percentiles=[.1, .25, .5, .75, .9, .95, .99])  # 自定义百分位
df.shape                 # (行数, 列数)
df.columns.tolist()      # 列名列表
df.index                 # 行索引
df.dtypes                # 每列数据类型
df.memory_usage(deep=True)  # 每列内存占用
df.nunique()             # 每列唯一值个数
```

### 3.4 数据选择与过滤

Pandas提供了四种主要的索引选择方式。

```python
# ---- 列选择 ----
df['薪资']                 # 返回Series
df[['姓名', '薪资']]       # 返回DataFrame

# ---- 布尔过滤 ----
df[df['年龄'] > 30]                        # 单条件
df[(df['年龄'] > 25) & (df['薪资'] > 6000)]  # 多条件（&符号）
df[(df['部门'] == '技术') | (df['部门'] == '市场')]  # 或条件（|符号）
df[df['部门'].isin(['技术', '市场'])]       # isin筛选
df[~df['部门'].isin(['运营'])]             # 排除
df[df['姓名'].str.contains('张')]           # 字符串匹配
df[(df['薪资'] > df['薪资'].median()) & (df['年龄'] < 35)] # 基于统计量的条件

# ---- 查询方法（类SQL语法）----
df.query('年龄 > 25 and 薪资 > 6000')
df.query('部门 in ["技术", "市场"]')

# ---- loc（标签索引）----
df.loc[0]                    # 选择行标签为0的行
df.loc[0:2]                  # 切片（loc切片包含右端点！）
df.loc[0, '姓名']            # 单个值
df.loc[0:2, ['姓名', '年龄']] # 行+列组合选择
df.loc[df['年龄'] > 30, ['姓名', '部门']]  # 条件行 + 指定列

df.set_index('姓名', inplace=True)
df.loc['张三']               # 按新索引选择

# ---- iloc（位置索引）----
df.iloc[0]                   # 第1行（位置索引，不包含右端点）
df.iloc[0:3]                 # 第0,1,2行
df.iloc[0:3, 1:3]            # 第0-2行，第1-2列
df.iloc[[0, 2, 4], [0, 3]]   # 通过整数列表选择

# ---- at / iat（标量快速访问）----
df.at[0, '薪资']             # 比loc更快（单值访问专用）
df.iat[0, 2]                 # 位置标量访问
```

### 3.5 数据修改

```python
# 新增列
df['年终奖'] = df['薪资'] * 0.2
df['年薪'] = df['薪资'] * 12 + df['年终奖']

# 基于条件创建列：np.where
df['薪资等级'] = np.where(df['薪资'] > 7000, '高', '低')

# 基于多条件：np.select
conditions = [
    df['年龄'] < 25,
    (df['年龄'] >= 25) & (df['年龄'] < 35),
    df['年龄'] >= 35
]
choices = ['青年', '中年', '资深']
df['年龄组'] = np.select(conditions, choices, default='未知')

# apply：按行/列自定义变换
df['薪资'].apply(lambda x: x * 1.05)  # 元素级
df[['薪资', '年龄']].apply(np.mean, axis=0)      # 按列（axis=0）
df[['薪资', '年龄']].apply(lambda row: row.max(), axis=1)  # 按行

# map：Series的映射方法
dept_map = {'技术': 'Technology', '市场': 'Marketing', '运营': 'Operations'}
df['部门英文'] = df['部门'].map(dept_map)

# 删除列
df.drop('年终奖', axis=1, inplace=True)
df.drop(columns=['年终奖', '年薪'], inplace=True)

# 删除行
df.drop(0, axis=0, inplace=True)        # 按索引删除
df.drop(df[df['薪资'] < 3000].index, inplace=True)  # 按条件删除

# 重命名列
df.rename(columns={'姓名': 'name', '年龄': 'age'}, inplace=True)
df.columns = ['name', 'age', 'salary', 'dept']  # 全部重命名

# 数据类型转换
df['age'] = df['age'].astype('int32')
df['薪资'] = pd.to_numeric(df['薪资'], errors='coerce') # 安全转换
df['date'] = pd.to_datetime(df['date'])
df['category'] = df['category'].astype('category')  # 节省内存
```

### 3.6 排序与排名

```python
# 按值排序
df.sort_values('薪资', ascending=False, inplace=True)
df.sort_values(['部门', '薪资'], ascending=[True, False])

# 按索引排序
df.sort_index(inplace=True)

# 排名
df['薪资排名'] = df['薪资'].rank(ascending=False)         # 从上到下
df['薪资排名_平局平均'] = df['薪资'].rank(method='average') # 平局取平均
df['薪资排名_平局最前'] = df['薪资'].rank(method='min')      # 平局取最小
df['薪资排名_密集'] = df['薪资'].rank(method='dense')       # 密集排名

# nlargest / nsmallest
df.nlargest(5, '薪资')     # 薪资最高的5条
df.nsmallest(3, '年龄')    # 年龄最小的3条
```

### 3.7 分组聚合（groupby）

分组聚合是数据分析的核心操作，遵循**split-apply-combine**模式。

```python
# 基本分组
df.groupby('部门')['薪资'].mean()

# 多列分组
df.groupby(['部门', '性别'])['薪资'].mean()

# 多函数聚合
df.groupby('部门')['薪资'].agg(['mean', 'sum', 'min', 'max', 'std', 'count'])

# 不同列不同聚合
df.groupby('部门').agg({
    '薪资': ['mean', 'sum'],
    '年龄': ['min', 'max'],
    '姓名': 'count'
})

# 命名聚合（Named Aggregation）
result = df.groupby('部门').agg(
    平均薪资=('薪资', 'mean'),
    总薪资=('薪资', 'sum'),
    人数=('薪资', 'count'),
    最大年龄=('年龄', 'max')
).reset_index()

# 自定义聚合函数
def salary_range(x):
    return x.max() - x.min()

def coefficient_of_variation(x):
    return x.std() / x.mean() * 100

df.groupby('部门')['薪资'].agg([salary_range, coefficient_of_variation])

# transform：保持原形状的分组变换
df['部门均值'] = df.groupby('部门')['薪资'].transform('mean')
df['相对部门均值'] = df['薪资'] - df['部门均值']

# filter：按分组条件过滤
df.groupby('部门').filter(lambda g: len(g) >= 5)  # 保留>=5人的部门

# 分组遍历
for dept, group in df.groupby('部门'):
    print(f"{dept}: {len(group)}人, 平均薪资{group['薪资'].mean():.0f}元")
```

### 3.8 数据透视表

```python
# pivot_table
pivot = pd.pivot_table(df,
                       values='薪资',
                       index='部门',
                       columns='年份',
                       aggfunc='mean',
                       fill_value=0,
                       margins=True,
                       margins_name='合计')

# 多values
pivot = pd.pivot_table(df,
                       values=['薪资', '年龄'],
                       index='部门',
                       aggfunc={'薪资': 'mean', '年龄': 'median'})

# crosstab：频数交叉表
# 原始：统计各部门各年龄段人数
pd.crosstab(df['部门'], df['年龄组'],
            margins=True,
            normalize='index')  # 按行归一化（比例）
```

### 3.9 数据合并

```python
# concat：沿轴拼接
result = pd.concat([df1, df2], axis=0, ignore_index=True)  # 行拼接
result = pd.concat([df1, df2], axis=1)                      # 列拼接

# merge：类似SQL JOIN
inner = pd.merge(df1, df2, on='key', how='inner')  # 内连接
left  = pd.merge(df1, df2, on='key', how='left')   # 左连接
right = pd.merge(df1, df2, on='key', how='right')  # 右连接
outer = pd.merge(df1, df2, on='key', how='outer')  # 外连接

# 不同列名连接
pd.merge(df1, df2, left_on='id', right_on='user_id')

# join：按索引合并
df1.join(df2, how='left', lsuffix='_left', rsuffix='_right')

# 处理重复列
pd.merge(df1, df2, on='key', suffixes=('_当前', '_上一期'))
```

### 3.10 时间序列

```python
# 创建时间序列
dates = pd.date_range('2024-01-01', periods=365, freq='D')
dates = pd.date_range('2024-01-01', '2024-12-31', freq='H')     # 每小时
dates = pd.date_range('2024-01-01', periods=12, freq='MS')      # 每月初
dates = pd.date_range('2024-01-01', periods=4, freq='QS')       # 每季初

# to_datetime：灵活解析
pd.to_datetime('2024-01-15')
pd.to_datetime(['2024/01/15', 'Jan 15, 2024'])
pd.to_datetime('20240115', format='%Y%m%d')

# 时间索引操作
df.set_index('date', inplace=True)
df['2024']                # 2024全年数据
df['2024-01']             # 2024年1月
df['2024-01-01':'2024-06-30']  # 日期范围

# 提取时间组件
df['year'] = df.index.year
df['month'] = df.index.month
df['day'] = df.index.day
df['dayofweek'] = df.index.dayofweek  # 周一=0, 周日=6
df['week'] = df.index.isocalendar().week
df['quarter'] = df.index.quarter
df['is_weekend'] = df.index.dayofweek >= 5

# resample：重采样
df.resample('W').sum()                       # 按周汇总
df.resample('M').agg(['sum', 'mean', 'count'])  # 按月多指标
df.resample('D').asfreq()                    # 转为日频（产生缺失值）

# 滚动窗口
df['MA_7'] = df['sales'].rolling(window=7).mean()         # 7日移动平均
df['MA_30'] = df['sales'].rolling(window=30).mean()       # 30日移动平均
df['volatility'] = df['returns'].rolling(window=30).std()  # 滚动波动率
df['rolling_max'] = df['sales'].rolling(window=7).max()
df['rolling_corr'] = df['A'].rolling(30).corr(df['B'])    # 滚动相关系数

# 指数加权移动平均
df['EWMA_7'] = df['sales'].ewm(span=7).mean()

# shift / diff / pct_change
df['prev_day'] = df['sales'].shift(1)          # 前一天值
df['diff_1'] = df['sales'].diff(1)             # 一阶差分
df['pct_change'] = df['sales'].pct_change()     # 环比变化率
df['pct_change_mom'] = df['sales'].pct_change(periods=1)   # 环比
df['pct_change_yoy'] = df['sales'].pct_change(periods=12)  # 同比

# 日期偏移
from pandas.tseries.offsets import Day, MonthEnd, YearBegin, Week
df.index + Day(7)          # 加7天
df.index + MonthEnd(0)     # 当月最后一天
df.index + MonthEnd(1)     # 下月最后一天
df.index - MonthBegin(2)   # 两月前的第一天
```

### 3.11 窗口函数

```python
# rolling：定长窗口
df['roll_mean'] = df['value'].rolling(window=5).mean()

# expanding：扩展窗口（从数据开始累积）
df['exp_mean'] = df['value'].expanding().mean()
df['exp_sum'] = df['value'].expanding().sum()

# ewm：指数加权窗口
df['ewm_mean'] = df['value'].ewm(alpha=0.3).mean()       # 指定alpha
df['ewm_mean'] = df['value'].ewm(span=10).mean()         # 指定span
df['ewm_mean'] = df['value'].ewm(halflife=3).mean()      # 指定半衰期
```

### 3.12 链式操作（Method Chaining）

推荐使用链式调用提升代码可读性：

```python
# 不推荐：多步骤中间变量
df1 = df[df['薪资'] > 5000]
df2 = df1.groupby('部门')
df3 = df2['薪资'].agg(['mean', 'sum'])
df4 = df3.sort_values('mean', ascending=False)
result = df4.round(2)

# 推荐：链式操作
result = (df[df['薪资'] > 5000]
          .groupby('部门')
          .agg(平均薪资=('薪资', 'mean'), 总薪资=('薪资', 'sum'))
          .sort_values('平均薪资', ascending=False)
          .round(2)
          .reset_index())

# pipe：管道函数（将自定义函数链入管道）
def add_features(df):
    return df.assign(
        total=lambda x: x['quantity'] * x['price'],
        month=lambda x: x['date'].dt.month
    )

def filter_valid(df, min_total):
    return df[df['total'] >= min_total]

result = (df
          .pipe(add_features)
          .pipe(filter_valid, min_total=100)
          .query('month >= 6'))
```

### 3.13 分类数据

```python
# 创建分类列——节省内存并加速操作
df['部门'] = df['部门'].astype('category')
df['部门'].cat.categories     # 查看分类级别
df['部门'].cat.codes          # 查看编码值（整数）
df['部门'].cat.reorder_categories(['技术', '市场', '运营', '人事'], ordered=True)

# 有序分类
quality = pd.Categorical(['优', '良', '中', '差'],
                          categories=['差', '中', '良', '优'],
                          ordered=True)

# 分类列的cut/qcut：连续值离散化
df['年龄组'] = pd.cut(df['年龄'], bins=[0, 25, 35, 50, 100],
                      labels=['青年', '壮年', '中年', '老年'])
df['薪资分位'] = pd.qcut(df['薪资'], q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'])  # 等频分箱
```

### 3.14 apply / applymap / map / transform 完整对比

| 方法 | 作用对象 | 输入 | 输出 | 典型场景 |
|------|---------|------|------|---------|
| `Series.map()` | Series | 标量 | Series | 字典映射、替换 |
| `Series.apply()` | Series | 标量 | Series | 逐元素自定义函数 |
| `DataFrame.apply()` | DataFrame | Series(列/行) | Series | 沿轴聚合/变换 |
| `DataFrame.applymap()` | DataFrame | 标量 | DataFrame | 逐元素操作 |
| `groupby.transform()` | GroupBy | Series | Series(同shape) | 分组后保持原形状 |
| `groupby.apply()` | GroupBy | DataFrame | 灵活 | 任意分组操作 |

```python
# 完整对比示例
df = pd.DataFrame({'A': [1, 2, 3], 'B': [10, 20, 30]})

# map：Series层面，适合字典映射
df['status'] = df['A'].map({1: '低', 2: '中', 3: '高'})

# apply (Series)：逐元素自定义逻辑
df['A_squared'] = df['A'].apply(lambda x: x ** 2)

# apply (DataFrame, axis=1)：逐行处理
df['row_sum'] = df[['A', 'B']].apply(lambda row: row['A'] + row['B'], axis=1)

# apply (DataFrame, axis=0)：逐列处理
df[['A', 'B']].apply(np.mean, axis=0)

# applymap：DataFrame逐元素
df[['A', 'B']] = df[['A', 'B']].applymap(lambda x: round(x, 2))

# transform：与groupby配合保持形状
df['zscore_by_group'] = df.groupby('category')['value'].transform(
    lambda x: (x - x.mean()) / x.std()
)
```

### 3.15 字符串方法（.str 访问器）

Pandas提供向量化的字符串操作，大幅加速文本列处理。

```python
s = pd.Series(['Alice_001', 'Bob_002', 'Charlie_003', None, 'David_004'])

# 基本操作（全部跳过NaN）
s.str.lower()                    # 转小写
s.str.upper()                    # 转大写
s.str.len()                      # 字符串长度
s.str.strip()                    # 去除两端空格

# 分割与提取
s.str.split('_')                 # 返回 Series of lists
s.str.split('_', expand=True)    # 展开为DataFrame（多列）
s.str.extract(r'(\d+)')          # 正则提取（按分组）
s.str.extract(r'([A-Za-z]+)_(\d+)')  # 多分组提取
s.str.extractall(r'(\d+)')       # 提取所有匹配项

# 匹配与替换
s.str.contains(r'\d{3}')         # 是否包含（布尔Series）
s.str.match(r'^[A-Z]')           # 从头匹配（全字符串匹配）
s.str.findall(r'(\w+)')          # 查找所有匹配
s.str.replace(r'_', '-')         # 正则替换
s.str.replace(r'_(\d+)', r'-\1', regex=True)  # 带反向引用

# 字符串拼接
pd.Series(['2024', '01', '15']).str.cat(sep='-')  # '2024-01-15'
s.str.slice(0, 5)                # 切片
```

---

## 第4章 Matplotlib与Seaborn数据可视化

### 4.1 可视化理论基础

数据可视化是数据分析的"眼睛"——在建模前看清数据的分布、关系、趋势和异常。

**可视化选型决策树**：

| 分析目的 | 推荐图表类型 | 使用函数 |
|---------|-------------|---------|
| 比较数值大小 | 柱状图、条形图 | `plt.bar()`, `sns.barplot()` |
| 展示趋势变化 | 折线图、面积图 | `plt.plot()`, `sns.lineplot()` |
| 展示分布形态 | 直方图、密度图、箱线图、小提琴图 | `plt.hist()`, `sns.histplot()`, `sns.boxplot()`, `sns.violinplot()` |
| 探索变量关系 | 散点图、气泡图、六边形热图 | `plt.scatter()`, `sns.scatterplot()`, `plt.hexbin()` |
| 展示构成比例 | 饼图、环形图、堆叠柱状图、树图 | `plt.pie()`, `plt.bar(stacked=True)` |
| 矩阵相关性 | 热力图、聚类热图 | `sns.heatmap()`, `sns.clustermap()` |
| 多变量对比 | 分面网格图、成对关系图 | `sns.FacetGrid()`, `sns.pairplot()` |
| 分类对比 | 箱线图、小提琴图、分类散点图 | `sns.catplot()`, `sns.stripplot()` |

### 4.2 Matplotlib基础架构

Matplotlib模仿MATLAB的绘图风格，采用**Figure-Axes-Artist**的三层架构：

- **Figure**（画布）：最顶层的容器，一幅图的整体
- **Axes**（坐标系）：实际的绘图区域，一个Figure可含多个Axes
- **Artist**（图形元素）：点、线、文本、图例等一切可见元素

```python
import matplotlib.pyplot as plt
import numpy as np

# Figure是顶层容器
fig = plt.figure(figsize=(10, 6), dpi=100, facecolor='white')

# Axes是绘图区域（每次add_subplot新增一个子图轴域）
ax1 = fig.add_subplot(2, 2, 1)  # 2行2列，第1个位置
ax2 = fig.add_subplot(2, 2, 2)  # 第2个位置
ax3 = fig.add_subplot(2, 2, 3)  # 第3个位置
ax4 = fig.add_subplot(2, 2, 4)  # 第4个位置

# 更简洁的子图创建
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
ax1, ax2, ax3, ax4 = axes.flatten()
```

### 4.3 Matplotlib核心绘图类型

```python
# 准备演示数据
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# ---- 折线图 ----
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(x, y1, 'b-', label='sin(x)', linewidth=2, alpha=0.8)
ax.plot(x, y2, 'r--', label='cos(x)', linewidth=2, alpha=0.8)

# 标记关键数据点
ax.plot(x[::10], y1[::10], 'bo', markersize=6, label='sin采样点')

# 标注与装饰
ax.set_title('三角函数曲线', fontsize=14, fontweight='bold')
ax.set_xlabel('x', fontsize=12)
ax.set_ylabel('y', fontsize=12)
ax.legend(loc='upper right', frameon=True, fontsize=10)
ax.grid(True, linestyle='--', alpha=0.6)
ax.set_xlim(0, 10)
ax.set_ylim(-1.5, 1.5)

# ---- 柱状图 ----
categories = ['Q1', 'Q2', 'Q3', 'Q4']
revenue_2023 = [120, 135, 150, 180]
revenue_2024 = [140, 155, 170, 210]

fig, ax = plt.subplots(figsize=(8, 5))
x_pos = np.arange(len(categories))
bar_width = 0.35
bars1 = ax.bar(x_pos - bar_width/2, revenue_2023, bar_width,
               label='2023', color='#3498db', edgecolor='white')
bars2 = ax.bar(x_pos + bar_width/2, revenue_2024, bar_width,
               label='2024', color='#e74c3c', edgecolor='white')

# 柱顶标注数值
for bar in bars1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            str(bar.get_height()), ha='center', va='bottom', fontsize=9)
for bar in bars2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            str(bar.get_height()), ha='center', va='bottom', fontsize=9)

ax.set_xticks(x_pos)
ax.set_xticklabels(categories)
ax.set_ylabel('营收（万元）', fontsize=12)
ax.set_title('2023-2024季度营收对比', fontsize=14, fontweight='bold')
ax.legend()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# ---- 散点图 ----
np.random.seed(42)
n = 100
x_scatter = np.random.randn(n) * 2
y_scatter = x_scatter * 1.5 + np.random.randn(n) * 3
colors = np.random.rand(n)
sizes = np.abs(np.random.randn(n) * 100 + 50)

fig, ax = plt.subplots(figsize=(8, 6))
scatter = ax.scatter(x_scatter, y_scatter, c=colors, s=sizes,
                     alpha=0.6, cmap='viridis', edgecolors='white',
                     linewidths=0.5)
ax.set_xlabel('特征 X', fontsize=12)
ax.set_ylabel('特征 Y', fontsize=12)
ax.set_title('多维度散点图（颜色=第三维，大小=第四维）', fontsize=14)
cbar = fig.colorbar(scatter, ax=ax, label='颜色映射')
ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

# ---- 直方图 ----
data1 = np.random.normal(0, 1, 1000)
data2 = np.random.normal(3, 1.5, 800)

fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(data1, bins=40, alpha=0.6, label='Group A', color='steelblue', density=True)
ax.hist(data2, bins=40, alpha=0.6, label='Group B', color='coral', density=True)
ax.set_xlabel('数值', fontsize=12)
ax.set_ylabel('概率密度', fontsize=12)
ax.set_title('两组数据分布直方图对比', fontsize=14)
ax.legend()

# ---- 箱线图 ----
data = [np.random.normal(0, std, 100) for std in range(1, 5)]

fig, ax = plt.subplots(figsize=(8, 5))
bp = ax.boxplot(data, patch_artist=True, labels=['σ=1', 'σ=2', 'σ=3', 'σ=4'])
for patch, color in zip(bp['boxes'], ['#3498db', '#2ecc71', '#e74c3c', '#9b59b6']):
    patch.set_facecolor(color)
ax.set_title('不同标准差数据的箱线图', fontsize=14)
ax.set_ylabel('数值', fontsize=12)
ax.grid(axis='y', linestyle='--', alpha=0.5)
```

### 4.4 Matplotlib高级功能

```python
# ---- 多子图布局：GridSpec ----
from matplotlib.gridspec import GridSpec

fig = plt.figure(figsize=(12, 8))
gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)

ax1 = fig.add_subplot(gs[0, :])      # 第1行占满3列 → 放标题或汇总图
ax2 = fig.add_subplot(gs[1:, 0])     # 第2-3行第1列
ax3 = fig.add_subplot(gs[1:, 1:])    # 第2-3行第2-3列

# 不规则的子图布局（拼接）
ax4 = fig.add_subplot(gs[1, 0])
ax5 = fig.add_subplot(gs[1, 1:])
ax6 = fig.add_subplot(gs[2, :2])
ax7 = fig.add_subplot(gs[2, 2])

# ---- 双Y轴 ----
fig, ax1 = plt.subplots(figsize=(10, 5))
ax2 = ax1.twinx()  # 共享X轴的第二个Y轴

dates = pd.date_range('2024-01-01', periods=12, freq='M')
sales = [100 + i*10 for i in range(12)]
price = [20 + np.sin(i)*5 for i in range(12)]

line1, = ax1.plot(dates, sales, 'b-', linewidth=2, label='销售额')
line2, = ax2.plot(dates, price, 'r--', linewidth=2, label='均价')

ax1.set_xlabel('日期', fontsize=12)
ax1.set_ylabel('销售额（万元）', color='blue', fontsize=12)
ax2.set_ylabel('均价（元）', color='red', fontsize=12)

# 合并图例
lines = [line1, line2]
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper left')

fig.autofmt_xdate(rotation=45)

# ---- 图形样式与配色 ----
# 内置样式
plt.style.use('ggplot')      # R语言ggplot风格
plt.style.use('seaborn-v0_8-darkgrid')  # seaborn深色网格
plt.style.use('bmh')         # 贝叶斯方法风格
plt.style.use('fivethirtyeight')  # 五三八统计风格
print(plt.style.available)   # 查看所有可用样式

# 自定义颜色映射
from matplotlib.colors import LinearSegmentedColormap

colors_list = ['#0d0887', '#46039f', '#7201a8', '#9c179e', '#bd3786',
               '#d8576b', '#ed7953', '#fb9f3a', '#fdca26', '#f0f921']
custom_cmap = LinearSegmentedColormap.from_list('custom', colors_list, N=256)

# 使用自定义颜色映射绘制热力图
data = np.random.rand(10, 10)
plt.figure(figsize=(8, 6))
plt.imshow(data, cmap=custom_cmap, aspect='auto')
plt.colorbar(label='自定义颜色映射')

# ---- 中文支持 ----
# Windows通常使用以下字体即可
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False   # 解决负号显示问题

# 也可运行时设置
import matplotlib
matplotlib.rc('font', family='SimHei', size=12)
matplotlib.rc('axes', unicode_minus=False)
```

### 4.5 Seaborn：统计可视化库

Seaborn 构建在Matplotlib之上，提供更高层的统计可视化接口，默认样式更美观，与Pandas DataFrame无缝集成。

```python
import seaborn as sns
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 设置全局样式
sns.set_theme(style='darkgrid', palette='muted', font_scale=1.2)

# 加载Seaborn内置数据集
tips = sns.load_dataset('tips')
iris = sns.load_dataset('iris')
diamonds = sns.load_dataset('diamonds').sample(5000, random_state=42)
```

**4.5.1 关系图（relplot）**

relplot 是Seaborn的推荐级接口——统一管理散点图和折线图的子图布局。

```python
# 散点图：展示变量间的关系
sns.relplot(data=tips, x='total_bill', y='tip',
            hue='smoker', style='time', size='size',
            palette='Set1', alpha=0.7, height=5)

# 分面散点图：按分类变量拆分子图
sns.relplot(data=tips, x='total_bill', y='tip',
            col='time', row='smoker',
            hue='sex', size='size',
            palette='viridis', height=4)

# ---- scatterplot（底层函数）----
fig, ax = plt.subplots(figsize=(8, 5))
sns.scatterplot(data=tips, x='total_bill', y='tip',
                hue='day', style='sex', size='size',
                sizes=(20, 200), alpha=0.7, ax=ax)

# ---- lineplot：趋势线（自动计算均值和置信区间）----
fmri = sns.load_dataset('fmri')
sns.relplot(data=fmri, x='timepoint', y='signal',
            hue='event', kind='line',
            estimator='mean', errorbar=('ci', 95),
            height=5, aspect=1.5)
```

**4.5.2 分布图（displot / histplot / kdeplot）**

```python
# distplot：分布图的推荐级接口（Seaborn 0.11+）
sns.displot(data=diamonds, x='price', kind='hist',
            bins=50, kde=True, height=5, aspect=1.5)

# 按分类分面的分布图
sns.displot(data=tips, x='total_bill', hue='time',
            kind='kde', fill=True, height=5, palette='Set2')

# 累积分布图（ECDF）
sns.displot(data=tips, x='total_bill', hue='day',
            kind='ecdf', height=5)

# ---- histplot（直方图底层函数）----
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
sns.histplot(data=tips, x='total_bill', bins=30, kde=True,
             hue='time', multiple='layer', ax=axes[0])
sns.histplot(data=tips, x='total_bill', bins=30, kde=True,
             hue='time', multiple='stack', ax=axes[1], shrink=0.8)

# ---- kdeplot（核密度估计底层函数）----
fig, ax = plt.subplots(figsize=(8, 5))
sns.kdeplot(data=tips, x='total_bill', hue='day',
            fill=True, alpha=0.3, palette='viridis', ax=ax)

# 二维KDE：二元分布密度等高线
sns.kdeplot(data=tips, x='total_bill', y='tip',
            cmap='Blues', fill=True, thresh=0, levels=100)

# ---- rugplot（边缘地毯图）----
sns.kdeplot(data=tips, x='total_bill')
sns.rugplot(data=tips, x='total_bill', height=0.05, alpha=0.3)
```

**4.5.3 分类图（catplot）**

catplot 是分类统计图的推荐级接口，按kind参数切换图表类型。

```python
# ---- 分类散点图（strip / swarm）----
# strip：少量抖动避免重叠
sns.catplot(data=tips, x='day', y='total_bill', kind='strip',
            jitter=True, hue='sex', dodge=True, height=5)

# swarm：智能排布，绝不重叠（数据量大时慢）
sns.catplot(data=tips, x='day', y='total_bill', kind='swarm',
            hue='sex', dodge=True, height=5)

# ---- 分类统计图（box / violin / boxen / bar / point）----
fig, axes = plt.subplots(2, 3, figsize=(18, 10))

# 箱线图：展示分位数
sns.boxplot(data=tips, x='day', y='total_bill', hue='smoker', ax=axes[0, 0])

# 小提琴图：展示分布密度
sns.violinplot(data=tips, x='day', y='total_bill', hue='smoker',
               split=True, inner='quartile', ax=axes[0, 1])

# boxen图：增强箱线（适合大数据集）
sns.boxenplot(data=diamonds, x='cut', y='price', ax=axes[0, 2])

# 棒图：展示均值+置信区间
sns.barplot(data=tips, x='day', y='total_bill', hue='sex',
            estimator='mean', errorbar=('ci', 95), ax=axes[1, 0])

# 点图：展示集中趋势+连线
sns.pointplot(data=tips, x='day', y='total_bill', hue='sex',
              dodge=True, markers=['o', 's'], ax=axes[1, 1])

# 计数图：展示分类频数
sns.countplot(data=tips, x='day', hue='sex', ax=axes[1, 2])

plt.tight_layout()
```

**4.5.4 回归图（lmplot / regplot）**

```python
# lmplot：分面回归拟合（推荐级接口）
sns.lmplot(data=tips, x='total_bill', y='tip',
           hue='smoker', col='time', row='sex',
           height=4, aspect=1)

# regplot：单图回归（底层函数）
fig, ax = plt.subplots(figsize=(8, 5))
sns.regplot(data=tips, x='total_bill', y='tip',
            scatter_kws={'alpha': 0.4, 's': 30},
            line_kws={'color': 'red', 'linewidth': 2},
            order=1,      # 多项式阶数（1=线性）
            ci=95,        # 置信区间
            ax=ax)

# 残差图：检验回归假设
sns.residplot(data=tips, x='total_bill', y='tip',
              lowess=True, scatter_kws={'alpha': 0.4})
```

**4.5.5 矩阵图（heatmap / clustermap）**

```python
# ---- 热力图：相关性矩阵可视化 ----
corr = df.corr(numeric_only=True)

fig, ax = plt.subplots(figsize=(10, 8))
mask = np.triu(np.ones_like(corr, dtype=bool))  # 上三角遮罩

sns.heatmap(corr,
            mask=mask,                  # 显示下三角
            annot=True,                 # 显示数值
            fmt='.2f',                  # 数值格式
            cmap='RdBu_r',              # 红蓝发散色 正相关=红，负相关=蓝
            vmin=-1, vmax=1,            # 颜色映射范围
            center=0,                   # 0值为白色中心
            square=True,                # 正方形格子
            linewidths=0.5,
            linecolor='white',
            cbar_kws={'shrink': 0.8, 'label': '相关系数'},
            ax=ax)
ax.set_title('特征相关性热力图', fontsize=14, fontweight='bold')

# 指定自定义配色
sns.heatmap(corr, cmap=sns.diverging_palette(250, 10, as_cmap=True),
            annot=True, fmt='.2f')

# ---- clustermap：带层次聚类的热力图 ----
sns.clustermap(corr,
               method='average',        # 聚类方法: single/complete/average/ward
               metric='correlation',    # 距离度量
               cmap='vlag',
               figsize=(10, 10),
               annot=True, fmt='.2f',
               row_cluster=True,        # 对行聚类
               col_cluster=True)        # 对列聚类
```

**4.5.6 成对关系图（pairplot）与联合分布图（jointplot）**

```python
# ---- pairplot：成对特征关系矩阵 ----
sns.pairplot(iris,
             hue='species',                 # 按类别着色
             diag_kind='hist',              # 对角线：hist/kde/auto
             corner=False,                  # True=只显示下三角
             palette='Set2',
             plot_kws={'alpha': 0.6, 's': 30},
             height=3)

# ---- jointplot：双变量联合分布 ----
# 带回归线
sns.jointplot(data=tips, x='total_bill', y='tip',
              kind='reg', height=7, ratio=5)

# 六边形热图（大数据集）
sns.jointplot(data=diamonds, x='carat', y='price',
              kind='hex', height=7, ratio=5,
              gridsize=30, cmap='Blues')

# KDE密度等高线
sns.jointplot(data=tips, x='total_bill', y='tip',
              kind='kde', height=7, fill=True, cmap='viridis')

# 残差联合图
sns.jointplot(data=tips, x='total_bill', y='tip',
              kind='resid', height=7)
```

### 4.6 Plotly交互式可视化（补充）

静态图用于报告，交互图用于探索分析。Plotly是Python最流行的交互式可视化库。

```python
import plotly.express as px
import plotly.graph_objects as go

# 交互式散点图（缩放、悬停、筛选）
fig = px.scatter(iris, x='sepal_length', y='petal_length',
                 color='species', size='petal_width',
                 hover_data=['sepal_width'],
                 title='鸢尾花——交互式散点矩阵')

# 交互式折线图
df_stock = px.data.stocks()
fig = px.line(df_stock, x='date', y=['GOOG', 'AAPL', 'AMZN'],
              title='科技股走势对比')

# 交互式热力图
fig = px.imshow(corr, text_auto='.2f', aspect='auto',
                color_continuous_scale='RdBu_r',
                title='交互式相关性热力图')

# 导出为HTML
fig.write_html('interactive_chart.html')
```

### 4.7 可视化最佳实践

1. **色彩选择**：对分类变量使用定性配色（tab10, Set2），对连续变量使用感知均匀配色（viridis, magma, plasma）
2. **避免冗余装饰**：3D效果、过度图例、繁复背景降低数据墨水比
3. **图表标注**：标题明确结论而非描述事实（"Q4营收环比增长21%"优于"各季度营收"）
4. **坐标轴起点**：柱状图通常应从0开始；折线图可截断以突显趋势
5. **一致性**：同一报告中同类型图表使用相同配色和风格
6. **可访问性**：为色盲读者选择色盲友好配色（如ColorBrewer、viridis系列）


---

## 第5章 数据清洗与预处理技术

### 5.1 数据清洗概览

真实数据永远不完美。数据清洗通常占数据分析总时间的60%-80%，是决定分析质量的关键步骤。

**典型数据质量问题**：

| 问题类型 | 表现 | 检测方法 |
|---------|------|---------|
| 缺失值 | 字段为空或NULL | `isnull().sum()` / `missingno`库 |
| 重复数据 | 完全相同或关键列重复的记录 | `duplicated().sum()` |
| 不一致格式 | 日期多种格式、单位不统一 | `dtype`检查 / 正则验证 |
| 异常值 | 极端值、不可能的值 | 箱线图 / Z-score / IQR |
| 数据类型错误 | 数值列存储为字符串 | `dtypes` / `pd.to_numeric(errors='coerce')` |
| 编码问题 | 中文乱码 | `chardet`检测编码 |
| 数据分布不均 | 类别严重不均衡 | `value_counts(normalize=True)` |
| 数据泄漏 | 未来信息混入训练集 | 按时间切分验证 |

### 5.2 缺失值处理

```python
import pandas as pd
import numpy as np
import missingno as msno

df = pd.DataFrame({
    'A': [1, 2, np.nan, 4, 5, np.nan, 7],
    'B': [np.nan, 2, 3, np.nan, 5, 6, 7],
    'C': ['x', 'y', np.nan, 'x', np.nan, 'z', 'x'],
    'D': [10.5, np.nan, 12.3, 14.1, np.nan, np.nan, 18.2]
})

# ---- 缺失值检测 ----
df.isnull()           # 布尔掩码
df.isnull().sum()     # 每列缺失计数
df.isnull().mean()    # 每列缺失比例
df.isnull().any(axis=1)  # 至少含一个缺失值的行

# 可视化缺失模式
import matplotlib.pyplot as plt
msno.matrix(df)           # 缺失值矩阵图
msno.bar(df)              # 缺失值柱状图
msno.heatmap(df)          # 缺失值相关性热图（缺失模式间的关联）
msno.dendrogram(df)       # 缺失模式层次聚类

# ---- 删除策略 ----
df.dropna()                     # 删除含任何缺失值的行
df.dropna(how='all')            # 仅删除全部缺失的行
df.dropna(thresh=3)             # 至少保留有3个非空值的行
df.dropna(subset=['A', 'B'])    # 仅基于指定列判断
df.dropna(axis=1)               # 删除含缺失值的列
df.dropna(axis=1, thresh=int(len(df) * 0.7))  # 删除缺失率>30%的列

# ---- 填充策略 ----
# 常数填充
df['A'].fillna(0, inplace=True)

# 统计量填充
df['A'].fillna(df['A'].mean(), inplace=True)     # 均值填充
df['A'].fillna(df['A'].median(), inplace=True)   # 中位数填充（对异常值更鲁棒）
df['C'].fillna(df['C'].mode()[0], inplace=True)  # 众数填充（分类变量）

# 前向/后向填充（时间序列）
df['B'].fillna(method='ffill', inplace=True)     # 前向填充（用上一个有效值）
df['B'].fillna(method='bfill', inplace=True)     # 后向填充（用下一个有效值）

# 插值填充（线性/多项式/样条）
df['D'] = df['D'].interpolate(method='linear')          # 线性插值
df['D'] = df['D'].interpolate(method='quadratic')       # 二次插值
df['D'] = df['D'].interpolate(method='cubic')           # 样条插值
df['D'] = df['D'].interpolate(method='time')            # 按时间索引插值

# 分组填充（每组按自己的统计量填充）
df['A'] = df.groupby('category')['A'].transform(lambda x: x.fillna(x.mean()))

# KNN填充
from sklearn.impute import KNNImputer
imputer = KNNImputer(n_neighbors=5, weights='distance')
df_filled = df.copy()
df_filled[['A', 'B', 'D']] = imputer.fit_transform(df[['A', 'B', 'D']])

# 多重插补（Multiple Imputation）
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer

mice_imputer = IterativeImputer(max_iter=20, random_state=42, n_nearest_features=5)
df_imputed = pd.DataFrame(
    mice_imputer.fit_transform(df.select_dtypes(include=[np.number])),
    columns=df.select_dtypes(include=[np.number]).columns
)

# ---- 缺失指示器（特征工程）----
# 保留缺失信息作为特征
df['A_was_missing'] = df['A'].isnull().astype(int)
```

**填充策略决策流程**：

1. 缺失率 > 50%：考虑删除该列
2. 缺失率 10%-50%：尝试模型填充或保留缺失指示变量
3. 缺失率 < 10%：均值/中位数/众数填充通常够用
4. 时间序列：优先用前向填充或插值
5. 非随机缺失（MNAR）：必须建模缺失机制，不能简单填充

### 5.3 重复数据处理

```python
# 检测重复行
df.duplicated().sum()                  # 完全重复行数
df.duplicated(subset=['user_id'])      # 按指定列检测
df.duplicated(keep='first')            # 标记后续重复（默认）
df.duplicated(keep=False)              # 标记所有重复（不保留任何）

# 删除重复行
df.drop_duplicates(inplace=True)                          # 完全重复
df.drop_duplicates(subset=['user_id', 'date'], inplace=True, keep='last')  # 保留最后一条

# 去重后按聚合规则归并（更精细的处理）
df_dedup = (df.groupby('user_id', as_index=False)
            .agg({
                'amount': 'sum',        # 金额求和
                'date': 'last',         # 保留最近日期
                'status': 'first',      # 保留初始状态
                'count': 'count'        # 记录重复次数
            }))
```

### 5.4 数据类型转换与优化

```python
# ---- 类型转换 ----
# 安全的数值转换
s = pd.Series(['1', '2', 'abc', '4.5', None])
pd.to_numeric(s, errors='coerce')   # coerce: 无法转换的变为NaN
pd.to_numeric(s, errors='raise')    # raise: 抛出异常
pd.to_numeric(s, errors='ignore')   # ignore: 保持原值

# 日期时间转换
dates = pd.Series(['2024-01-15', '01/15/2024', '2024.01.15', 'invalid'])
pd.to_datetime(dates, format='mixed', errors='coerce', dayfirst=False)

# 统一转换多个日期格式
pd.to_datetime(dates, format='%Y-%m-%d', errors='coerce')
pd.to_datetime(dates, infer_datetime_format=True)   # 自动推断格式

# ---- 内存优化 ----
# 查看当前内存占用（深拷贝统计，否则字符串/对象列不准）
df.info(memory_usage='deep')

# 整数降级
df['small_int'] = pd.to_numeric(df['small_int'], downcast='integer')

# 浮点数降级
df['small_float'] = pd.to_numeric(df['small_float'], downcast='float')

# 字符串 → 分类（重复值多时大幅节省内存）
df['category_col'] = df['category_col'].astype('category')

# 批量优化
def optimize_dtypes(df):
    """自动优化DataFrame数据类型以降低内存占用"""
    for col in df.columns:
        col_type = df[col].dtype
        if col_type != 'object' and col_type != 'category':
            c_min, c_max = df[col].min(), df[col].max()
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
            else:
                df[col] = pd.to_numeric(df[col], downcast='float')
        elif df[col].nunique() / len(df) < 0.5:   # 唯一值比例<50%
            df[col] = df[col].astype('category')
    return df
```

### 5.5 文本数据清洗

```python
import re

# ---- 字符串清洗 ----
# 去除首尾空格
df['name'] = df['name'].str.strip()

# 替换特殊字符
df['phone'] = df['phone'].str.replace(r'[\s\-\(\)\+]', '', regex=True)

# 统一大小写
df['city'] = df['city'].str.lower().str.title()

# ---- 正则表达式清洗 ----
# 提取数字
df['price_num'] = df['price'].str.extract(r'(\d+\.?\d*)').astype(float)

# 提取邮箱
pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
emails = df['info'].str.extract(f'({pattern})')

# 提取中文
df['cname'] = df['mixed'].str.extract(r'([一-鿿]+)')

# 验证手机号格式
valid = df['phone'].str.match(r'^1[3-9]\d{9}$')

# ---- 复杂替换 ----
# 多规则替换
translation_map = {
    r'\bBJ\b': '北京',
    r'\bSH\b': '上海',
    r'\bGZ\b': '广州',
    r'\bSZ\b': '深圳'
}
for pattern, replacement in translation_map.items():
    df['city'] = df['city'].str.replace(pattern, replacement, regex=True)

# ---- 文本切分与展开 ----
# 多值分隔（如标签列）
df_tags = df['tags'].str.split('|', expand=True)  # 展开为多列
df_tags.columns = [f'tag_{i+1}' for i in range(df_tags.shape[1])]

# 逐行explode
df_exploded = df.assign(tag=df['tags'].str.split('|')).explode('tag')
```

### 5.6 异常值检测与处理

```python
# ---- 方法1：IQR（四分位距）法 ----
def detect_outliers_iqr(data, column, multiplier=1.5):
    """使用IQR法检测异常值"""
    Q1 = data[column].quantile(0.25)
    Q3 = data[column].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - multiplier * IQR
    upper = Q3 + multiplier * IQR
    outliers = (data[column] < lower) | (data[column] > upper)
    return outliers, lower, upper

outlier_mask, lower, upper = detect_outliers_iqr(df, 'price', multiplier=1.5)

# ---- 方法2：Z-Score法（适用于正态分布）----
from scipy import stats
z_scores = np.abs(stats.zscore(df['price'].dropna()))
outlier_mask_z = z_scores > 3  # 3σ原则

# ---- 方法3：修正Z-Score（对异常值本身更鲁棒）----
def modified_zscore(series):
    """基于MAD（中位数绝对偏差）的修正Z-Score"""
    median = series.median()
    mad = np.median(np.abs(series - median))
    mad = 1.4826 * mad  # 修正因子使MAD与标准差尺度一致
    return 0.6745 * (series - median) / mad  # 0.6745使MAD~SD于正态下一致

mod_z = modified_zscore(df['price'].dropna())

# ---- 方法4：孤立森林（Isolation Forest，适用于多维异常）----
from sklearn.ensemble import IsolationForest
iso_forest = IsolationForest(contamination=0.05, random_state=42)
outlier_labels = iso_forest.fit_predict(df[['price', 'quantity', 'age']])
# -1=异常样本, 1=正常样本

# ---- 方法5：DBSCAN聚类（基于密度的异常检测）----
from sklearn.cluster import DBSCAN
dbscan = DBSCAN(eps=0.5, min_samples=5)
clusters = dbscan.fit_predict(scaled_features)
# -1标签表示噪声点（异常值）

# ---- 异常值处理策略 ----
# 策略1：删除
df_clean = df[~outlier_mask].copy()

# 策略2：截断（Winsorization / Clipping）
df['price_clipped'] = df['price'].clip(lower=lower, upper=upper)

# 策略3：对数变换（压缩右偏分布）
df['price_log'] = np.log1p(df['price'])  # log(1+x)，可处理零值

# 策略4：分位数变换（转成均匀分布或正态分布）
from sklearn.preprocessing import QuantileTransformer
qt = QuantileTransformer(output_distribution='normal', random_state=42)
df['price_normal'] = qt.fit_transform(df[['price']])

# 策略5：标记后单独建模（保留信息）
df['is_outlier'] = outlier_mask.astype(int)
```

**异常值处理决策**：
- 明显的数据录入错误 → 删除或修正
- 真实但不具代表性的极端值 → 截断或分箱
- 需要保留的极端业务价值（高价值客户） → 标记后分层建模

### 5.7 特征缩放与变换

```python
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler, RobustScaler,
    PowerTransformer, QuantileTransformer,
    Normalizer, LabelEncoder, OrdinalEncoder,
    OneHotEncoder, KBinsDiscretizer
)

# ---- 数值特征缩放 ----
X = df[['age', 'income', 'score']].values

# StandardScaler：Z-score标准化（均值0，方差1）→ 适合PCA/聚类/线性模型
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
# 恢复：scaler.inverse_transform(X_scaled)

# MinMaxScaler：归一到[0,1] → 适合神经网络/基于距离的算法
scaler = MinMaxScaler(feature_range=(0, 1))
X_normalized = scaler.fit_transform(X)

# RobustScaler：用中位数和IQR缩放 → 对异常值不敏感
scaler = RobustScaler(quantile_range=(25.0, 75.0))
X_robust = scaler.fit_transform(X)

# ---- 分布变换（使偏态数据接近正态）----
# Box-Cox（仅正数）
from scipy.stats import boxcox
df['income_boxcox'], lambda_param = boxcox(df['income'] + 1)  # +1处理零值

# Yeo-Johnson（可处理负数/零值）→ 比Box-Cox更通用
pt = PowerTransformer(method='yeo-johnson', standardize=True)
df['income_yj'] = pt.fit_transform(df[['income']])

# QuantileTransformer：映射到均匀分布或正态分布
qt_uniform = QuantileTransformer(output_distribution='uniform',
                                  n_quantiles=100, random_state=42)
qt_normal = QuantileTransformer(output_distribution='normal',
                                 n_quantiles=100, random_state=42)

# ---- 分类特征编码 ----
# LabelEncoder：单个分类列 → 整数 （注意：引入了序关系，仅适用于树模型）
from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
df['city_encoded'] = le.fit_transform(df['city'])

# OrdinalEncoder：多个分类列 → 整数
ord_enc = OrdinalEncoder()
df[['city', 'education']] = ord_enc.fit_transform(df[['city', 'education']])

# OneHotEncoder：分类 → 独热编码（哑变量）
ohe = OneHotEncoder(sparse_output=False, drop='first', handle_unknown='ignore')
ohe_features = ohe.fit_transform(df[['city']])
ohe_columns = ohe.get_feature_names_out(['city'])
df_ohe = pd.DataFrame(ohe_features, columns=ohe_columns)

# pandas的get_dummies（日常探索更方便）
df_dummies = pd.get_dummies(df, columns=['city', 'education'],
                            drop_first=True, dtype='int8')

# 高基数分类处理：Target Encoding / Frequency Encoding
# 频率编码：用每个类别出现的频数代替原类别
df['city_freq'] = df['city'].map(df['city'].value_counts(normalize=True))

# 目标编码：用每类的目标均值代替（注意信息泄漏，需交叉验证）
df['city_target_enc'] = df.groupby('city')['target'].transform('mean')
```

---

## 第6章 探索性数据分析与统计分析

### 6.1 EDA方法论

探索性数据分析（EDA, Exploratory Data Analysis）由统计学家John Tukey创立，核心理念是**在建模之前先用图表和统计量理解数据**。

**EDA系统框架**：

1. **单变量分析**：逐一检查每个变量的分布、集中趋势、离散度
2. **双变量分析**：研究变量间两两关系（相关、差异、交互）
3. **多变量分析**：同时考虑3+个变量，如分面可视化、降维投影
4. **缺失分析与质量评估**：缺失模式、异常值分布、数据偏差

### 6.2 描述性统计量

```python
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# ---- 集中趋势 ----
mean = df['salary'].mean()           # 均值：对异常值敏感
median = df['salary'].median()       # 中位数：对异常值鲁棒
mode = df['salary'].mode()           # 众数：适合分类变量
trimmed_mean = stats.trim_mean(df['salary'], 0.1)  # 10%截尾均值

# ---- 离散程度 ----
std = df['salary'].std(ddof=1)       # 样本标准差（ddof=1为无偏估计）
var = df['salary'].var(ddof=1)       # 样本方差
mad = stats.median_abs_deviation(df['salary'])  # 中位数绝对偏差（鲁棒）
iqr = df['salary'].quantile(0.75) - df['salary'].quantile(0.25)  # IQR
coeff_var = df['salary'].std() / df['salary'].mean() * 100  # 变异系数(%)

# ---- 分布形态 ----
skewness = df['salary'].skew()       # 偏度：>0右偏，<0左偏，=0对称
kurtosis = df['salary'].kurtosis()   # 峰度：>0尖峰，<0扁平峰
# 正态性检验
stat, p_value = stats.normaltest(df['salary'].dropna())  # D'Agostino K²检验
stat, p_value = stats.shapiro(df['salary'].dropna()[:5000])  # Shapiro-Wilk（≤5000）

# ---- 分位数系统 ----
quantiles = df['salary'].quantile([0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0])

# ---- 一键生成全面统计报告 ----
# pandas-profiling / ydata-profiling
from ydata_profiling import ProfileReport
profile = ProfileReport(df, title='数据分析报告', explorative=True)
profile.to_file('report.html')
```

### 6.3 相关性与关联度量

```python
# ---- Pearson相关系数（线性相关，对异常值敏感）----
corr_pearson = df[['age', 'income', 'score', 'years_exp']].corr(method='pearson')

# ---- Spearman秩相关系数（单调相关，对异常值鲁棒）----
corr_spearman = df[['age', 'income', 'score', 'years_exp']].corr(method='spearman')

# ---- Kendall τ 相关系数（序相关，更鲁棒但计算更慢）----
corr_kendall = df[['age', 'income', 'score', 'years_exp']].corr(method='kendall')

# ---- 相关系数显著性检验 ----
r, p_value = stats.pearsonr(df['age'].dropna(), df['income'].dropna())
rho, p_value = stats.spearmanr(df['age'].dropna(), df['income'].dropna())

# ---- 分类-数值关联 ----
# Eta系数（ANOVA-based，类似分类×数值的R²）
def eta_squared(categorical, numeric):
    """计算分类变量对数值变量的解释度（η²）"""
    from scipy.stats import f_oneway
    groups = [numeric[categorical == cat].dropna() for cat in categorical.unique()]
    if len(groups) < 2:
        return 0
    f_stat, p_val = f_oneway(*groups)
    ss_between = sum(len(g) * (g.mean() - numeric.mean())**2 for g in groups)
    ss_total = ((numeric - numeric.mean())**2).sum()
    return ss_between / ss_total if ss_total > 0 else 0

# ---- 分类-分类关联 ----
# Cramér's V（基于卡方检验的关联强度，0~1）
def cramers_v(confusion_matrix):
    """计算分类变量的Cramér's V关联强度"""
    chi2 = stats.chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    min_dim = min(confusion_matrix.shape[0], confusion_matrix.shape[1]) - 1
    if min_dim == 0 or n == 0:
        return 0
    return np.sqrt(chi2 / (n * min_dim))

contingency_table = pd.crosstab(df['city'], df['education'])
cramers_v_value = cramers_v(contingency_table)

# ---- 互信息（Mutual Information）：捕获任意类型关联（含非线性）----
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression

# 数值特征对分类目标的关联
mi_scores = mutual_info_classif(df.select_dtypes(include=[np.number]),
                                 df['target'], random_state=42)
mi_series = pd.Series(mi_scores, index=df.select_dtypes(include=[np.number]).columns)
mi_series.sort_values(ascending=False)
```

### 6.4 假设检验体系

```python
from scipy import stats

# ====== 参数检验（假定数据服从正态分布）======

# ---- 单样本t检验：样本均值是否等于指定值 ----
t_stat, p_value = stats.ttest_1samp(df['score'].dropna(), popmean=70)
# H₀: μ = 70, H₁: μ ≠ 70

# ---- 独立双样本t检验：两组均值是否相等 ----
group_a = df[df['group'] == 'A']['score'].dropna()
group_b = df[df['group'] == 'B']['score'].dropna()
t_stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=True)   # 假设方差齐性
t_stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)  # Welch's t-test（不假设方差齐性）

# ---- 配对t检验：同一样本前后测 ----
before = df['score_before'].dropna()
after = df['score_after'].dropna()
t_stat, p_value = stats.ttest_rel(before, after)

# ---- 单因素方差分析（ANOVA）：多组均值比较 ----
groups = [df[df['city'] == c]['income'].dropna() for c in df['city'].unique()]
f_stat, p_value = stats.f_oneway(*groups)

# 事后检验（Tukey HSD）：找出具体哪些组间有差异
from statsmodels.stats.multicomp import pairwise_tukeyhsd
tukey_result = pairwise_tukeyhsd(df['income'].dropna(), df['city'], alpha=0.05)
print(tukey_result)

# ====== 非参数检验（不要求正态分布）======

# ---- Mann-Whitney U检验（Wilcoxon秩和）：两组独立样本位置参数是否相等 ----
u_stat, p_value = stats.mannwhitneyu(group_a, group_b, alternative='two-sided')

# ---- Wilcoxon符号秩检验：配对样本差异 ----
w_stat, p_value = stats.wilcoxon(before, after)

# ---- Kruskal-Wallis H检验：多组样本位置参数（非参数ANOVA）----
h_stat, p_value = stats.kruskal(*groups)

# ---- 卡方独立性检验：分类变量间是否独立 ----
contingency_table = pd.crosstab(df['city'], df['education'])
chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)

# ---- Kolmogorov-Smirnov检验：两个分布是否相同 ----
ks_stat, p_value = stats.ks_2samp(group_a, group_b)

# ---- Levene检验：多组方差是否齐性 ----
levene_stat, p_value = stats.levene(*groups)

# ====== 效应量（不仅报告显著性，还要报告实际效果大小）======
# Cohen's d：标准化均值差
def cohens_d(group1, group2):
    diff = np.mean(group1) - np.mean(group2)
    pooled_std = np.sqrt((np.std(group1, ddof=1)**2 + np.std(group2, ddof=1)**2) / 2)
    return diff / pooled_std
# 解释：0.2=小效应，0.5=中效应，0.8=大效应

# 多重检验校正
from statsmodels.stats.multitest import multipletests
p_values = [0.001, 0.01, 0.03, 0.05, 0.10, 0.20, 0.50]
rejected, corrected_p, _, _ = multipletests(p_values, method='bonferroni')
# methods: 'bonferroni', 'holm', 'fdr_bh'(Benjamini-Hochberg), 'fdr_by'
```

### 6.5 置信区间与Bootstrap

```python
# ---- 均值的置信区间（正态假设）----
def mean_confidence_interval(data, confidence=0.95):
    """计算均值的置信区间"""
    n = len(data)
    mean = np.mean(data)
    se = stats.sem(data)  # 标准误 = std / sqrt(n)
    h = se * stats.t.ppf((1 + confidence) / 2, n - 1)  # t分布临界值
    return mean - h, mean, mean + h

ci_lower, mean, ci_upper = mean_confidence_interval(df['salary'].dropna())

# ---- Bootstrap置信区间（无需分布假设）----
def bootstrap_ci(data, statistic=np.mean, n_bootstrap=10000, confidence=0.95):
    """Bootstrap法计算任意统计量的置信区间"""
    boot_stats = np.empty(n_bootstrap)
    n = len(data)
    for i in range(n_bootstrap):
        sample = np.random.choice(data, size=n, replace=True)
        boot_stats[i] = statistic(sample)
    alpha = 1 - confidence
    lower = np.percentile(boot_stats, 100 * alpha / 2)
    upper = np.percentile(boot_stats, 100 * (1 - alpha / 2))
    return lower, np.mean(boot_stats), upper

ci_lower, boot_mean, ci_upper = bootstrap_ci(df['salary'].dropna())
```

### 6.6 数据分布拟合

```python
from scipy import stats

# ---- 拟合特定分布 ----
# 拟合正态分布
mu, sigma = stats.norm.fit(df['salary'].dropna())
# 拟合对数正态分布
shape, loc, scale = stats.lognorm.fit(df['salary'].dropna())
# 拟合Gamma分布
alpha, loc, beta = stats.gamma.fit(df['salary'].dropna())
# 拟合指数分布
loc, scale = stats.expon.fit(df['salary'].dropna())

# ---- Q-Q图（分位数-分位数图）：直观检查分布拟合 ----
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
stats.probplot(df['salary'].dropna(), dist="norm", plot=axes[0])
axes[0].set_title('正态分布Q-Q图')

stats.probplot(np.log1p(df['salary'].dropna()), dist="norm", plot=axes[1])
axes[1].set_title('对数变换后Q-Q图')

stats.probplot(stats.boxcox(df['salary'].dropna() + 1)[0], dist="norm", plot=axes[2])
axes[2].set_title('Box-Cox变换后Q-Q图')

# ---- 分布拟合优度检验 ----
# Kolmogorov-Smirnov检验
ks_stat, p_value = stats.kstest(df['salary'].dropna(), 'norm',
                                 args=(mu, sigma))
# Anderson-Darling检验（对尾部更敏感）
result = stats.anderson(df['salary'].dropna(), dist='norm')
```

### 6.7 辛普森悖论与混淆变量检测

辛普森悖论：分组时各子组呈现的方向与汇总数据方向相反的现象，是数据探索中容易被忽略的陷阱。

```python
# 演示辛普森悖论
# 整体趋势 vs 分组趋势
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 整体散点（看起来正相关）
sns.regplot(data=df, x='feature', y='target', ax=axes[0], scatter_kws={'alpha':0.5})
axes[0].set_title('整体趋势（可能误导）')

# 分组散点（各组反而是负相关或无关）
sns.scatterplot(data=df, x='feature', y='target', hue='group',
                ax=axes[1], alpha=0.6)
for group, gdf in df.groupby('group'):
    sns.regplot(data=gdf, x='feature', y='target', ax=axes[1],
                scatter=False, label=f'{group}单独趋势')
axes[1].set_title('分组趋势揭示辛普森悖论')

# 检测方法：检查分组后相关系数符号是否翻转
overall_r = df['feature'].corr(df['target'])
group_rs = df.groupby('group')[['feature', 'target']].corr().iloc[0::2, -1]
print(f"整体r={overall_r:.3f}, 分组r={group_rs.values}")
```

---

## 第7章 机器学习入门（面向数据分析）

### 7.1 机器学习工作流概述

数据分析中的机器学习聚焦于**探索预测能力、发现特征重要性、生成业务洞察**，而非单纯追求模型精度。

**标准工作流**：
1. 问题定义与指标选择（回归? 分类? 聚类? 用什么业务指标衡量成功?）
2. 数据划分（训练集/验证集/测试集 + 时间序列按时间划分）
3. 特征工程与预处理流水线构建
4. 基线模型建立（简单的规则或线性模型）
5. 多模型对比（从简单到复杂逐步尝试）
6. 模型解释与洞察提取（这才是数据分析的最终产出）

```python
from sklearn.model_selection import (
    train_test_split, cross_val_score, StratifiedKFold,
    KFold, TimeSeriesSplit, GridSearchCV, RandomizedSearchCV
)
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    mean_absolute_error, mean_squared_error, r2_score,
    mean_absolute_percentage_error
)
```

### 7.2 数据划分策略

```python
# ---- 简单随机划分 ----
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y  # 分类问题需分层抽样
)

# ---- 分层K折交叉验证（分类/回归通用）----
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

# ---- 时间序列划分（严禁随机打乱！）----
tscv = TimeSeriesSplit(n_splits=5)
for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

# ---- 分组划分（组不交叉，避免数据泄漏）----
from sklearn.model_selection import GroupKFold
gkf = GroupKFold(n_splits=5)
for train_idx, val_idx in gkf.split(X, y, groups=df['user_id']):
    pass  # 同一用户的样本不会同时出现在训练集和验证集中
```

### 7.3 预处理流水线（Pipeline）

```python
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder, OrdinalEncoder
from sklearn.impute import SimpleImputer

# 定义特征分组
numeric_features = ['age', 'income', 'score', 'years_exp', 'distance']
categorical_features_ohe = ['city', 'education']       # 低基数 → 独热编码
categorical_features_ord = ['frequency']                # 有序 → 序数编码

# 数值特征预处理流水线
numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),          # 中位数填充缺失值
    ('scaler', StandardScaler())                            # Z-score标准化
])

# 分类特征（独热编码）预处理流水线
categorical_transformer_ohe = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
])

# 分类特征（有序编码）预处理流水线
categorical_transformer_ord = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('ordinal', OrdinalEncoder())
])

# 组装完整的特征预处理
preprocessor = ColumnTransformer(transformers=[
    ('num', numeric_transformer, numeric_features),
    ('cat_ohe', categorical_transformer_ohe, categorical_features_ohe),
    ('cat_ord', categorical_transformer_ord, categorical_features_ord)
])

# 完整的机器学习流水线（预处理 + 模型）
from sklearn.linear_model import LogisticRegression

full_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', LogisticRegression(max_iter=1000, random_state=42))
])

# 一键训练
full_pipeline.fit(X_train, y_train)

# 一键预测
y_pred = full_pipeline.predict(X_test)
y_proba = full_pipeline.predict_proba(X_test)[:, 1]   # 正类概率

# 交叉验证评估整套流水线（Pipeline内的每一步都在每折内重做，无泄漏）
cv_scores = cross_val_score(full_pipeline, X, y,
                            cv=StratifiedKFold(5, shuffle=True, random_state=42),
                            scoring='roc_auc')
print(f"CV AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
```

### 7.4 回归模型

```python
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor

# 建立模型对比池
models = {
    'Linear Regression': LinearRegression(),
    'Ridge': Ridge(alpha=1.0),
    'Lasso': Lasso(alpha=0.1),
    'ElasticNet': ElasticNet(alpha=0.1, l1_ratio=0.5),
    'Decision Tree': DecisionTreeRegressor(max_depth=5, random_state=42),
    'Random Forest': RandomForestRegressor(n_estimators=100, max_depth=10,
                                            random_state=42, n_jobs=-1),
    'Gradient Boosting': GradientBoostingRegressor(n_estimators=100, max_depth=3,
                                                    learning_rate=0.1, random_state=42),
    'SVR': SVR(kernel='rbf', C=1.0),
    'KNN': KNeighborsRegressor(n_neighbors=5, weights='distance')
}

# 对比评估
results = {}
for name, model in models.items():
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', model)
    ])
    cv_scores = cross_val_score(pipeline, X, y,
                                cv=5, scoring='neg_mean_absolute_error')
    results[name] = {
        'MAE': -cv_scores.mean(),
        'MAE_std': cv_scores.std(),
        'RMSE': np.sqrt(-cross_val_score(pipeline, X, y, cv=5,
                                          scoring='neg_mean_squared_error')).mean()
    }

results_df = pd.DataFrame(results).T.sort_values('MAE')
print(results_df.round(4))
```

### 7.5 分类模型

```python
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB

# 模型对比池
classifiers = {
    'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
    'Decision Tree': DecisionTreeClassifier(max_depth=5, random_state=42),
    'Random Forest': RandomForestClassifier(n_estimators=100, max_depth=10,
                                              class_weight='balanced',
                                              random_state=42, n_jobs=-1),
    'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, max_depth=3,
                                                     learning_rate=0.1, random_state=42),
    'SVM': SVC(kernel='rbf', probability=True, random_state=42),
    'KNN': KNeighborsClassifier(n_neighbors=5),
    'Naive Bayes': GaussianNB()
}

for name, clf in classifiers.items():
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', clf)
    ])
    cv_scores = cross_val_score(pipeline, X, y,
                                cv=StratifiedKFold(5, shuffle=True, random_state=42),
                                scoring='roc_auc')
    print(f"{name:25s}  AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
```

### 7.6 超参数调优

```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

# ---- 网格搜索 ----
param_grid = {
    'classifier__n_estimators': [100, 200, 500],
    'classifier__max_depth': [5, 10, 15, None],
    'classifier__min_samples_split': [2, 5, 10],
    'classifier__min_samples_leaf': [1, 2, 4],
    'classifier__max_features': ['sqrt', 'log2', None]
}

pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(random_state=42, n_jobs=-1))
])

grid_search = GridSearchCV(
    pipeline, param_grid, cv=5,
    scoring='roc_auc', n_jobs=-1, verbose=1,
    return_train_score=True
)
grid_search.fit(X_train, y_train)
print(f"最佳参数: {grid_search.best_params_}")
print(f"最佳AUC: {grid_search.best_score_:.4f}")

# ---- 随机搜索（比网格搜索高效，高维空间推荐）----
from scipy.stats import randint, uniform

param_distributions = {
    'classifier__n_estimators': randint(50, 500),
    'classifier__max_depth': randint(3, 30),
    'classifier__min_samples_split': randint(2, 20),
    'classifier__min_samples_leaf': randint(1, 10),
    'classifier__max_features': ['sqrt', 'log2', None],
    'classifier__class_weight': ['balanced', 'balanced_subsample', None]
}

random_search = RandomizedSearchCV(
    pipeline, param_distributions,
    n_iter=50, cv=5, scoring='roc_auc',
    n_jobs=-1, random_state=42, verbose=1
)
random_search.fit(X_train, y_train)
```

### 7.7 分类指标详解

```python
# 混淆矩阵
cm = confusion_matrix(y_test, y_pred)

# 可视化
fig, ax = plt.subplots(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['预测负类', '预测正类'],
            yticklabels=['实际负类', '实际正类'], ax=ax)
ax.set_title('混淆矩阵', fontsize=14, fontweight='bold')

# 完整报告
from sklearn.metrics import classification_report
print(classification_report(y_test, y_pred, target_names=['非违约', '违约']))

# AUC-ROC曲线
from sklearn.metrics import roc_curve, auc
fpr, tpr, thresholds = roc_curve(y_test, y_proba)
roc_auc = auc(fpr, tpr)

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC曲线 (AUC = {roc_auc:.3f})')
ax.plot([0, 1], [0, 1], 'r--', linewidth=1, label='随机猜测 (AUC = 0.5)')
ax.fill_between(fpr, tpr, alpha=0.2)
ax.set_xlabel('假阳性率 (FPR)', fontsize=12)
ax.set_ylabel('真阳性率 (TPR / Recall)', fontsize=12)
ax.set_title('ROC曲线', fontsize=14, fontweight='bold')
ax.legend(loc='lower right')
ax.set_xlim([0.0, 1.0])
ax.set_ylim([0.0, 1.05])
ax.grid(True, linestyle='--', alpha=0.6)

# Precision-Recall曲线（不平衡分类更应关注PR）
from sklearn.metrics import precision_recall_curve, average_precision_score
precision, recall, _ = precision_recall_curve(y_test, y_proba)
ap = average_precision_score(y_test, y_proba)

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(recall, precision, 'g-', linewidth=2, label=f'PR曲线 (AP = {ap:.3f})')
ax.set_xlabel('召回率 (Recall)', fontsize=12)
ax.set_ylabel('精确率 (Precision)', fontsize=12)
ax.set_title('精确率-召回率曲线', fontsize=14, fontweight='bold')
ax.legend()
ax.grid(True, linestyle='--', alpha=0.6)
```

### 7.8 回归指标详解

```python
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error,
    mean_absolute_percentage_error, r2_score,
    explained_variance_score, max_error
)

def regression_report(y_true, y_pred, n_features=None):
    """生成完整的回归模型评估报告"""
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mape = mean_absolute_percentage_error(y_true, y_pred) * 100
    r2 = r2_score(y_true, y_pred)
    explained_var = explained_variance_score(y_true, y_pred)
    max_err = max_error(y_true, y_pred)

    # 调整R²（惩罚特征数量）
    n = len(y_true)
    if n_features and n > n_features + 1:
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - n_features - 1)
    else:
        adj_r2 = r2

    return pd.DataFrame({
        '指标': ['MAE', 'MSE', 'RMSE', 'MAPE(%)', 'R²', 'Adj_R²', 'Explained_Var', 'Max_Error'],
        '值': [mae, mse, rmse, mape, r2, adj_r2, explained_var, max_err]
    })

print(regression_report(y_test, y_pred, n_features=X_train.shape[1]))

# ---- 残差诊断图 ----
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

residuals = y_test - y_pred

# 残差vs拟合值（检查线性/同方差假设）
axes[0].scatter(y_pred, residuals, alpha=0.5, edgecolors='white')
axes[0].axhline(y=0, color='red', linestyle='--', linewidth=1.5)
axes[0].set_xlabel('预测值', fontsize=12)
axes[0].set_ylabel('残差', fontsize=12)
axes[0].set_title('残差 vs 预测值（检测异方差）', fontsize=13)

# 残差Q-Q图
stats.probplot(residuals, dist="norm", plot=axes[1])
axes[1].set_title('残差正态Q-Q图', fontsize=13)

# 实际vs预测散点图
axes[2].scatter(y_test, y_pred, alpha=0.5, edgecolors='white')
axes[2].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()],
             'r--', linewidth=1.5, label='完美预测')
axes[2].set_xlabel('实际值', fontsize=12)
axes[2].set_ylabel('预测值', fontsize=12)
axes[2].set_title(f'实际值 vs 预测值 (R²={r2_score(y_test, y_pred):.3f})', fontsize=13)
axes[2].legend()

plt.tight_layout()
```

### 7.9 特征重要性与模型解释

模型解释是数据分析区别于纯机器学习工程的关键——产出洞见而非仅仅产出预测。

```python
# ---- 方法1：树模型内置特征重要性 ----
rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
rf.fit(X_train_processed, y_train)

feature_importance = pd.DataFrame({
    '特征': feature_names,
    '重要性': rf.feature_importances_
}).sort_values('重要性', ascending=False)

fig, ax = plt.subplots(figsize=(10, 6))
sns.barplot(data=feature_importance.head(15), y='特征', x='重要性',
            palette='viridis', ax=ax)
ax.set_title('特征重要性（随机森林）', fontsize=14, fontweight='bold')

# ---- 方法2：排列重要性（Permutation Importance，模型无关）----
from sklearn.inspection import permutation_importance

result = permutation_importance(
    pipeline, X_test, y_test,
    n_repeats=10, random_state=42, n_jobs=-1,
    scoring='roc_auc'
)

perm_importance = pd.DataFrame({
    '特征': feature_names,
    '重要性均值': result.importances_mean,
    '重要性标准差': result.importances_std
}).sort_values('重要性均值', ascending=False)

fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(perm_importance['特征'].head(15)[::-1],
        perm_importance['重要性均值'].head(15)[::-1],
        xerr=perm_importance['重要性标准差'].head(15)[::-1],
        color='steelblue', edgecolor='white')
ax.set_title('排列重要性（模型无关）', fontsize=14, fontweight='bold')

# ---- 方法3：SHAP值（最有解释力的方法）----
import shap

# 创建SHAP解释器（对树模型使用TreeExplainer，速度极快）
explainer = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X_test_processed)

# SHAP摘要图
shap.summary_plot(shap_values, X_test_processed,
                  feature_names=feature_names,
                  plot_type='dot', max_display=15)

# SHAP条形图（平均绝对值）
shap.summary_plot(shap_values, X_test_processed,
                  feature_names=feature_names,
                  plot_type='bar', max_display=15)

# 单个样本解释（瀑布图）
shap.waterfall_plot(shap.Explanation(values=shap_values[0],
                     base_values=explainer.expected_value,
                     data=X_test_processed[0],
                     feature_names=feature_names))

# 特征依赖图（展示单一特征的SHAP值随特征值的变化）
shap.dependence_plot('income', shap_values, X_test_processed,
                     feature_names=feature_names)

# ---- 方法4：部分依赖图（PDP）----
from sklearn.inspection import PartialDependenceDisplay

features_to_plot = [0, 1, 2]  # 要画的特征索引
PartialDependenceDisplay.from_estimator(
    rf, X_train_processed, features_to_plot,
    feature_names=feature_names, grid_resolution=50
)
```

### 7.10 聚类分析

聚类是无监督学习的核心技术，用于发现数据的自然分组。

```python
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

# ---- K-Means ----
# 肘部法确定最佳K值
inertias = []
silhouette_scores = []
K_range = range(2, 15)

for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    inertias.append(kmeans.inertia_)
    silhouette_scores.append(silhouette_score(X_scaled, labels))

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].plot(K_range, inertias, 'bo-')
axes[0].set_xlabel('K值', fontsize=12)
axes[0].set_ylabel('簇内平方和（Inertia）', fontsize=12)
axes[0].set_title('肘部法——选择最佳K值', fontsize=14)

axes[1].plot(K_range, silhouette_scores, 'ro-')
axes[1].set_xlabel('K值', fontsize=12)
axes[1].set_ylabel('轮廓系数', fontsize=12)
axes[1].set_title('轮廓系数——评估聚类质量', fontsize=14)
axes[1].axhline(y=max(silhouette_scores), color='gray', linestyle='--',
                label=f'最佳={max(silhouette_scores):.3f} (K={K_range[np.argmax(silhouette_scores)]})')
axes[1].legend()

# 执行最终聚类
optimal_k = K_range[np.argmax(silhouette_scores)]
kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
df['cluster'] = kmeans.fit_predict(X_scaled)

# 聚类画像：每簇的特征均值
cluster_profile = df.groupby('cluster')[numeric_features].mean()
print(cluster_profile)

# ---- DBSCAN（密度聚类，可自动发现离群点）----
from sklearn.neighbors import NearestNeighbors

# 确定eps参数
neighbors = NearestNeighbors(n_neighbors=5)
neighbors_fit = neighbors.fit(X_scaled)
distances, indices = neighbors_fit.kneighbors(X_scaled)
distances = np.sort(distances[:, -1])

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(distances)
ax.set_xlabel('数据点（按距离排序）', fontsize=12)
ax.set_ylabel(f'第5近邻距离', fontsize=12)
ax.set_title('K-距离图（确定DBSCAN的eps参数）\n寻找"膝盖"拐点', fontsize=13)

# eps取拐点处的距离值
dbscan = DBSCAN(eps=0.5, min_samples=5)
df['dbscan_cluster'] = dbscan.fit_predict(X_scaled)
# -1标签 = 噪声/离群点

# ---- 高斯混合模型（GMM，软聚类）----
gmm = GaussianMixture(n_components=3, random_state=42)
df['gmm_cluster'] = gmm.fit_predict(X_scaled)
df['gmm_proba'] = gmm.predict_proba(X_scaled).max(axis=1)  # 每个点的归属概率

# 模型选择（BIC/AIC）
n_components_range = range(1, 15)
bic_scores = [GaussianMixture(n, random_state=42).fit(X_scaled).bic(X_scaled)
              for n in n_components_range]
aic_scores = [GaussianMixture(n, random_state=42).fit(X_scaled).aic(X_scaled)
              for n in n_components_range]

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(n_components_range, bic_scores, 'o-', label='BIC')
ax.plot(n_components_range, aic_scores, 'o-', label='AIC')
ax.set_xlabel('高斯组件数', fontsize=12)
ax.set_ylabel('信息准则得分', fontsize=12)
ax.set_title('BIC/AIC——选择GMM组件数（越低越好）', fontsize=14)
ax.legend()

# ---- 层次聚类 ----
from scipy.cluster.hierarchy import dendrogram, linkage

# 计算连接矩阵
linkage_matrix = linkage(X_scaled, method='ward')

# 谱系图（树状图）
fig, ax = plt.subplots(figsize=(14, 6))
dendrogram(linkage_matrix, truncate_mode='level', p=10,
           leaf_rotation=90, leaf_font_size=10)
ax.set_title('层次聚类树状图', fontsize=14, fontweight='bold')
ax.set_xlabel('样本索引（聚合后）', fontsize=12)
ax.set_ylabel('距离', fontsize=12)

# 按树状图切割
from scipy.cluster.hierarchy import fcluster
labels = fcluster(linkage_matrix, t=3, criterion='maxclust')

# 或直接使用sklearn接口
agg = AgglomerativeClustering(n_clusters=3, linkage='ward')
df['agg_cluster'] = agg.fit_predict(X_scaled)
```

### 7.11 降维技术

```python
from sklearn.decomposition import PCA, TruncatedSVD, NMF, FactorAnalysis
from sklearn.manifold import TSNE, MDS, Isomap

# ---- PCA（主成分分析）----
pca = PCA()
X_pca = pca.fit_transform(X_scaled)

# 方差解释比——选择主成分数
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# 各主成分单独方差解释比
axes[0].bar(range(1, len(pca.explained_variance_ratio_) + 1),
            pca.explained_variance_ratio_, color='steelblue', edgecolor='white')
axes[0].set_xlabel('主成分', fontsize=12)
axes[0].set_ylabel('方差解释比', fontsize=12)
axes[0].set_title('各主成分的方差解释比', fontsize=14)

# 累计方差解释比
cumsum_var = np.cumsum(pca.explained_variance_ratio_)
axes[1].plot(range(1, len(cumsum_var) + 1), cumsum_var, 'bo-', markersize=4)
axes[1].axhline(y=0.8, color='red', linestyle='--', label='80%阈值')
axes[1].axhline(y=0.95, color='orange', linestyle='--', label='95%阈值')
axes[1].set_xlabel('主成分数', fontsize=12)
axes[1].set_ylabel('累计方差解释比', fontsize=12)
axes[1].set_title('累计方差解释比', fontsize=14)
axes[1].legend()
axes[1].grid(True, linestyle='--', alpha=0.5)

# 以保留95%方差为目标选择n_components
pca_95 = PCA(n_components=0.95, random_state=42)
X_pca_95 = pca_95.fit_transform(X_scaled)
print(f"选择 {pca_95.n_components_} 个主成分，保留 {pca_95.explained_variance_ratio_.sum():.1%} 方差")

# 载荷矩阵（主成分与原始特征的相关系数）
loadings = pd.DataFrame(
    pca.components_.T,
    columns=[f'PC{i+1}' for i in range(pca.n_components_)],
    index=feature_names
)

# 可视化前两个主成分的载荷
fig, ax = plt.subplots(figsize=(10, 8))
for i, feature in enumerate(feature_names):
    ax.arrow(0, 0, loadings.iloc[i, 0], loadings.iloc[i, 1],
             head_width=0.02, head_length=0.03, fc='steelblue', ec='steelblue', alpha=0.7)
    ax.text(loadings.iloc[i, 0] * 1.15, loadings.iloc[i, 1] * 1.15,
            feature, fontsize=9)
ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%})', fontsize=12)
ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%})', fontsize=12)
ax.set_title('PCA载荷图（Biplot）', fontsize=14, fontweight='bold')
ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
ax.set_xlim(-1, 1)
ax.set_ylim(-1, 1)
ax.grid(True, linestyle='--', alpha=0.3)

# ---- t-SNE（流形学习，可视化专用）----
# 注意：t-SNE不适合降维后建模，仅用于可视化探索
tsne = TSNE(n_components=2, perplexity=30, random_state=42, n_jobs=-1)
X_tsne = tsne.fit_transform(X_scaled)

fig, ax = plt.subplots(figsize=(10, 8))
scatter = ax.scatter(X_tsne[:, 0], X_tsne[:, 1],
                     c=df['target'] if 'target' in df.columns else df['cluster'],
                     cmap='viridis', alpha=0.7, edgecolors='white', linewidths=0.3)
ax.set_title('t-SNE可视化（流形投影）', fontsize=14, fontweight='bold')
ax.set_xlabel('t-SNE分量1', fontsize=12)
ax.set_ylabel('t-SNE分量2', fontsize=12)
cbar = plt.colorbar(scatter, ax=ax)
```

---

## 第8章 实战案例分析

### 8.1 综合案例1：电商用户行为分析

**业务背景**：某电商平台需要分析用户行为模式，识别高价值用户特征，为精准营销提供数据支持。

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# ---- 步骤1：数据加载与初探 ----
# 模拟电商数据集
np.random.seed(42)
n_users = 5000

orders = pd.DataFrame({
    'order_id': range(1, 20001),
    'user_id': np.random.choice(range(1, n_users + 1), 20000),
    'order_date': pd.date_range('2024-01-01', periods=20000, freq='87min'),
    'product_category': np.random.choice(
        ['电子产品', '服装', '食品', '家居', '图书', '美妆'], 20000,
        p=[0.20, 0.25, 0.15, 0.15, 0.10, 0.15]
    ),
    'quantity': np.random.poisson(2, 20000),
    'unit_price': np.random.lognormal(3, 0.8, 20000)
})
orders['total_amount'] = orders['quantity'] * orders['unit_price']

print(f"数据集: {orders.shape[0]}条订单, {orders['user_id'].nunique()}个用户")
print(f"时间跨度: {orders['order_date'].min()} ~ {orders['order_date'].max()}")

# ---- 步骤2：数据清洗 ----
# 检查缺失值与重复
print(f"缺失值:\n{orders.isnull().sum()}")
print(f"重复订单: {orders.duplicated(subset=['order_id']).sum()}")

# 过滤异常金额（保留1%-99%分位之间的）
q_low, q_high = orders['total_amount'].quantile([0.01, 0.99])
orders_clean = orders[(orders['total_amount'] >= q_low) &
                      (orders['total_amount'] <= q_high)].copy()

# ---- 步骤3：RFM用户分层 ----
# RFM: Recency(最近购买时间), Frequency(购买频次), Monetary(消费金额)
reference_date = orders_clean['order_date'].max() + pd.Timedelta(days=1)

rfm = orders_clean.groupby('user_id').agg({
    'order_date': lambda x: (reference_date - x.max()).days,   # R: 距今天数
    'order_id': 'count',                                        # F: 订单数
    'total_amount': 'sum'                                       # M: 总消费
}).rename(columns={
    'order_date': 'Recency',
    'order_id': 'Frequency',
    'total_amount': 'Monetary'
})

# RFM打分（按分位数分为4档，1最低4最高）
for col in ['Recency', 'Frequency', 'Monetary']:
    if col == 'Recency':  # Recency越小越好
        rfm[f'{col}_Score'] = pd.qcut(rfm[col], q=4,
                                       labels=[4, 3, 2, 1]).astype(int)
    else:  # Frequency和Monetary越大越好
        rfm[f'{col}_Score'] = pd.qcut(rfm[col], q=4,
                                       labels=[1, 2, 3, 4]).astype(int)

rfm['RFM_Score'] = rfm['Recency_Score'] + rfm['Frequency_Score'] + rfm['Monetary_Score']

# 用户分层定义
def classify_customer(score):
    if score >= 10: return '高价值客户'
    elif score >= 7: return '潜力客户'
    elif score >= 5: return '一般客户'
    elif score >= 3: return '低价值客户'
    else: return '流失客户'

rfm['Segment'] = rfm['RFM_Score'].apply(classify_customer)

# ---- 步骤4：可视化分析 ----
fig, axes = plt.subplots(2, 3, figsize=(18, 10))

# 用户分层饼图
segment_counts = rfm['Segment'].value_counts()
colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c', '#95a5a6']
axes[0, 0].pie(segment_counts.values, labels=segment_counts.index,
               autopct='%1.1f%%', colors=colors, startangle=90)
axes[0, 0].set_title('用户分层占比', fontsize=14, fontweight='bold')

# RFM三维散点
seg_colors = {'高价值客户': '#2ecc71', '潜力客户': '#3498db',
               '一般客户': '#f39c12', '低价值客户': '#e74c3c', '流失客户': '#95a5a6'}
for seg, color in seg_colors.items():
    seg_data = rfm[rfm['Segment'] == seg]
    axes[0, 1].scatter(seg_data['Recency'], seg_data['Monetary'],
                       c=color, label=seg, alpha=0.5, s=20)
axes[0, 1].set_xlabel('Recency（天数）', fontsize=11)
axes[0, 1].set_ylabel('Monetary（总消费）', fontsize=11)
axes[0, 1].set_title('Recency vs Monetary', fontsize=13)
axes[0, 1].legend(fontsize=7, markerscale=2)
axes[0, 1].grid(True, linestyle='--', alpha=0.3)

# 品类销售占比
category_sales = orders_clean.groupby('product_category')['total_amount'].sum().sort_values(ascending=False)
axes[0, 2].barh(category_sales.index, category_sales.values,
                color=sns.color_palette('viridis', len(category_sales)))
axes[0, 2].set_xlabel('销售额', fontsize=11)
axes[0, 2].set_title('各品类销售额', fontsize=13)

# 月度销售趋势
orders_clean['month'] = orders_clean['order_date'].dt.to_period('M')
monthly_sales = orders_clean.groupby('month')['total_amount'].sum()
monthly_sales.index = monthly_sales.index.astype(str)
axes[1, 0].plot(monthly_sales.index, monthly_sales.values, 'o-',
                color='#3498db', linewidth=2, markersize=6)
axes[1, 0].set_title('月度销售趋势', fontsize=13)
axes[1, 0].tick_params(axis='x', rotation=45)
axes[1, 0].grid(True, linestyle='--', alpha=0.5)

# RFM各维度分布
for i, col in enumerate(['Recency', 'Frequency', 'Monetary']):
    axes[1, 1 + (i > 0)].hist(rfm[col], bins=50, color=sns.color_palette('viridis', 3)[i],
                              alpha=0.7, edgecolor='white')
    axes[1, 1 + (i > 0)].set_title(f'{col}分布', fontsize=13)
    if col == 'Monetary':
        axes[1, 1 + (i > 0)].set_xscale('log')

plt.suptitle('电商用户行为分析看板', fontsize=18, fontweight='bold', y=1.01)
plt.tight_layout()

# ---- 步骤5：高价值用户特征画像 ----
high_value = rfm[rfm['Segment'] == '高价值客户']
print(f"\n=== 高价值用户特征 ===")
print(f"人数: {len(high_value)} ({len(high_value)/len(rfm)*100:.1f}%)")
print(f"平均Recency: {high_value['Recency'].mean():.0f}天")
print(f"平均Frequency: {high_value['Frequency'].mean():.1f}次")
print(f"平均Monetary: ¥{high_value['Monetary'].mean():.2f}")
print(f"贡献总消费: ¥{high_value['Monetary'].sum():.2f} "
      f"({high_value['Monetary'].sum()/rfm['Monetary'].sum()*100:.1f}%)")

# ---- 步骤6：业务建议 ----
print(f"""
=== 运营建议 ===
1. 高价值客户（{len(high_value)}人, {len(high_value)/len(rfm)*100:.1f}%）：
   → 专属客服、VIP权益、新品内测资格
2. 潜力客户（{(rfm['Segment']=='潜力客户').sum()}人）：
   → 满减券、会员升级引导、品类推荐
3. 流失客户（{(rfm['Segment']=='流失客户').sum()}人）：
   → 大力度召回优惠、流失原因调研
""")
```

### 8.2 综合案例2：A/B测试分析与统计验证

**业务背景**：产品团队对注册页面做了改版（新版本B），需要判断新版本是否显著提升了注册转化率。

```python
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

# ---- 模拟A/B测试数据 ----
np.random.seed(42)
n_a, n_b = 5000, 5000

# A组（旧版）：基线转化率12%
conversions_a = np.random.binomial(1, 0.12, n_a)
# B组（新版）：假设转化率提升到14%
conversions_b = np.random.binomial(1, 0.14, n_b)

df_ab = pd.DataFrame({
    'group': ['A'] * n_a + ['B'] * n_b,
    'converted': list(conversions_a) + list(conversions_b)
})

# ---- 描述统计 ----
ab_summary = df_ab.groupby('group')['converted'].agg([
    ('样本量', 'count'),
    ('转化数', 'sum'),
    ('转化率', 'mean')
]).round(4)
print(ab_summary)

# ---- 卡方独立性检验 ----
contingency = pd.crosstab(df_ab['group'], df_ab['converted'])
chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

print(f"\n卡方统计量: {chi2:.4f}")
print(f"p值: {p_value:.4f}")
print(f"自由度: {dof}")
print(f"结论: {'显著差异' if p_value < 0.05 else '无显著差异'} (α=0.05)")

# ---- 转化率差异的置信区间 ----
p_a = ab_summary.loc['A', '转化率']
p_b = ab_summary.loc['B', '转化率']
diff = p_b - p_a

# 比例差的标准误
se = np.sqrt(p_a*(1-p_a)/n_a + p_b*(1-p_b)/n_b)
z_critical = stats.norm.ppf(0.975)  # 95%置信区间对应的z值
ci_lower = diff - z_critical * se
ci_upper = diff + z_critical * se

print(f"\n转化率差异: {diff:.4f} ({diff*100:.2f}个百分点)")
print(f"95%置信区间: [{ci_lower:.4f}, {ci_upper:.4f}]")
print(f"即: [{ci_lower*100:.2f}pp, {ci_upper*100:.2f}pp]")

# ---- 统计功效分析（Power Analysis）----
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportions_ztest

effect_size = 2 * (np.arcsin(np.sqrt(p_b)) - np.arcsin(np.sqrt(p_a)))
power_analysis = NormalIndPower()
required_n = power_analysis.solve_power(
    effect_size=effect_size, power=0.80, alpha=0.05, ratio=1.0
)
print(f"\n所需最小样本量（power=0.80）: {required_n:.0f}每组")
print(f"当前样本量: {n_a}每组")

# ---- 可视化 ----
fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# 转化率对比柱状图
axes[0].bar(['旧版(A)', '新版(B)'], [p_a, p_b],
            color=['#3498db', '#2ecc71'], edgecolor='white', width=0.5)
# 添加置信区间误差线
for i, (p, n) in enumerate(zip([p_a, p_b], [n_a, n_b])):
    ci = z_critical * np.sqrt(p * (1 - p) / n)
    axes[0].errorbar(i, p, yerr=ci, capsize=10, color='black', linewidth=1.5)
axes[0].set_ylabel('转化率', fontsize=12)
axes[0].set_title('各组转化率对比（含95%CI）', fontsize=14, fontweight='bold')
axes[0].set_ylim(0, max(p_a, p_b) * 1.5)
axes[0].grid(axis='y', linestyle='--', alpha=0.4)

# 转化率差异的置信区间（森林图）
axes[1].axvline(x=0, color='red', linestyle='--', linewidth=1.5)
axes[1].errorbar(diff, 0, xerr=[[diff - ci_lower], [ci_upper - diff]],
                 fmt='o', capsize=10, color='#2ecc71', markersize=10, linewidth=2)
axes[1].set_xlabel('转化率差异 (B - A)', fontsize=12)
axes[1].set_title(f'转化率提升: {diff*100:.2f}pp\n95%CI: [{ci_lower*100:.2f}pp, {ci_upper*100:.2f}pp]',
                  fontsize=13)
axes[1].set_xlim(ci_lower - 0.01, ci_upper + 0.01)

# 样本量与统计功效关系曲线
sample_sizes = np.arange(500, 10000, 100)
powers = [NormalIndPower().power(effect_size, n, alpha=0.05, ratio=1)
          for n in sample_sizes]
axes[2].plot(sample_sizes, powers, 'b-', linewidth=2)
axes[2].axhline(y=0.80, color='red', linestyle='--', label='80%功效')
axes[2].axvline(x=n_a, color='green', linestyle='--', label=f'当前样本量={n_a}')
axes[2].set_xlabel('每组样本量', fontsize=12)
axes[2].set_ylabel('统计功效 (1-β)', fontsize=12)
axes[2].set_title('样本量与统计功效的关系', fontsize=14, fontweight='bold')
axes[2].legend()
axes[2].grid(True, linestyle='--', alpha=0.4)

plt.suptitle('A/B测试分析报告', fontsize=18, fontweight='bold', y=1.02)
plt.tight_layout()

# ---- 报告输出 ----
print(f"""
======== A/B测试分析结论 ========

测试概况：
  A组（旧版）：{n_a}用户, 转化率 {p_a:.2%}
  B组（新版）：{n_b}用户, 转化率 {p_b:.2%}

统计推断：
  转化率绝对提升：{diff*100:.2f}个百分点（相对提升: {(diff/p_a)*100:.1f}%）
  95%置信区间：[{ci_lower*100:.2f}pp, {ci_upper*100:.2f}pp]
  p值：{p_value:.4f} {'（显著）' if p_value < 0.05 else '（不显著）'}
  统计功效：{power_analysis.power(effect_size, n_a, alpha=0.05, ratio=1):.1%}

业务建议：{'建议全量上线新版' if p_value < 0.05 and diff > 0 else '收集更多数据后重新评估' if p_value > 0.05 else '新版本无显著优势，不建议上线'}
""")
```

### 8.3 综合案例3：销售预测与特征工程

**业务背景**：连锁零售企业需要预测未来30天各门店的销售额，以优化库存与人员排班。

```python
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.inspection import permutation_importance

# ---- 步骤1：构建模拟零售数据 ----
np.random.seed(42)
dates = pd.date_range('2022-01-01', '2024-12-31', freq='D')
stores = ['门店A', '门店B', '门店C']

data = []
for store in stores:
    for date in dates:
        base_sales = {'门店A': 5000, '门店B': 3500, '门店C': 4500}[store]
        # 趋势（年增长10%）
        trend = 1 + 0.10 * (date.year - 2022 + date.dayofyear / 365)
        # 季节性（7月最高，1月最低）
        seasonality = 1 + 0.3 * np.sin(2 * np.pi * (date.dayofyear - 180) / 365)
        # 星期效应（周末高）
        weekday_effect = 1.15 if date.dayofweek >= 5 else 1.0
        # 月底效应（发薪日）
        month_end_effect = 1.10 if date.day >= 25 else 1.0
        # 节假日效应
        holiday_effect = 1.25 if date.month in [1, 2, 12] and date.day < 10 else 1.0
        # 噪声
        noise = np.random.normal(0, 0.1)

        sales = base_sales * trend * seasonality * weekday_effect * month_end_effect * holiday_effect * (1 + noise)

        data.append({
            'date': date,
            'store': store,
            'sales': max(int(sales), 0),
            'day_of_week': date.dayofweek,
            'month': date.month,
            'year': date.year,
            'day_of_month': date.day,
            'is_weekend': int(date.dayofweek >= 5),
            'is_month_end': int(date.day >= 25),
            'quarter': date.quarter,
            'day_of_year': date.dayofyear
        })

df_sales = pd.DataFrame(data)

# ---- 步骤2：特征工程 ----
df_feat = df_sales.copy()

# 时间滞后特征
for lag in [1, 2, 3, 7, 14, 28, 365]:  # 1天前, 2天前, ..., 365天前
    df_feat[f'sales_lag_{lag}'] = df_feat.groupby('store')['sales'].shift(lag)

# 滚动窗口特征
for window in [7, 14, 30, 90]:
    roll = df_feat.groupby('store')['sales'].rolling(window, min_periods=1)
    df_feat[f'sales_roll_mean_{window}d'] = roll.mean().droplevel(0)
    df_feat[f'sales_roll_std_{window}d'] = roll.std().droplevel(0)
    df_feat[f'sales_roll_max_{window}d'] = roll.max().droplevel(0)
    df_feat[f'sales_roll_min_{window}d'] = roll.min().droplevel(0)

# 同比特征（去年同期）
df_feat['sales_yoy_lag_365'] = df_feat.groupby('store')['sales'].shift(365)

# 日期编码（循环编码——避免12月→1月的断崖）
df_feat['month_sin'] = np.sin(2 * np.pi * df_feat['month'] / 12)
df_feat['month_cos'] = np.cos(2 * np.pi * df_feat['month'] / 12)
df_feat['dow_sin'] = np.sin(2 * np.pi * df_feat['day_of_week'] / 7)
df_feat['dow_cos'] = np.cos(2 * np.pi * df_feat['day_of_week'] / 7)

# 门店One-Hot编码
df_feat = pd.get_dummies(df_feat, columns=['store'], drop_first=False)

# 删除含有NaN的行（滞后特征产生的）
df_feat = df_feat.dropna()

# ---- 步骤3：数据划分与建模 ----
# 按时间排序后划分
df_feat = df_feat.sort_values('date')  # 对每个门店分别排序
train_cutoff = '2024-09-30'
X_all = df_feat.drop(columns=['date', 'sales'])
y = df_feat['sales']

# 严格按时间先后划分
train_mask = df_feat['date'] <= train_cutoff
test_mask = df_feat['date'] > train_cutoff

X_train = X_all[train_mask]
y_train = y[train_mask]
X_test = X_all[test_mask]
y_test = y[test_mask]

print(f"训练集: {len(X_train):,}样本 ({df_feat[train_mask]['date'].min().date()} ~ {df_feat[train_mask]['date'].max().date()})")
print(f"测试集: {len(X_test):,}样本 ({df_feat[test_mask]['date'].min().date()} ~ {df_feat[test_mask]['date'].max().date()})")

# 训练模型
model = GradientBoostingRegressor(
    n_estimators=200, max_depth=5, learning_rate=0.05,
    subsample=0.8, random_state=42
)
model.fit(X_train, y_train)

# 预测
y_pred = model.predict(X_test)

# ---- 步骤4：评估 ----
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mape = mean_absolute_percentage_error(y_test, y_pred) * 100
r2 = r2_score(y_test, y_pred)

print(f"\n=== 模型评估 ===")
print(f"MAE: {mae:.0f}")
print(f"RMSE: {rmse:.0f}")
print(f"MAPE: {mape:.2f}%")
print(f"R²: {r2:.4f}")

# ---- 步骤5：特征重要性 ----
importances = pd.DataFrame({
    'feature': X_train.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(f"\n=== Top 10 特征 ===")
print(importances.head(10).to_string(index=False))

# ---- 步骤6：预测可视化 ----
fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)

colors = ['#3498db', '#2ecc71', '#e74c3c']
for i, store in enumerate(stores):
    store_mask = df_feat[test_mask]['store_门店A' if i == 0 else f'store_{store}'] == 1
    store_dates = df_feat[test_mask][store_mask].index

    axes[i].plot(df_feat.loc[store_dates, 'date'].values,
                 y_test.values[test_mask.values.nonzero()[0][X_test.index.isin(store_dates)]],
                 label='实际值', color=colors[i], alpha=0.7, linewidth=1.5)
    axes[i].plot(df_feat.loc[store_dates, 'date'].values,
                 y_pred[X_test.index.isin(store_dates)],
                 label='预测值', color='black', alpha=0.7, linestyle='--', linewidth=1.5)
    axes[i].fill_between(
        df_feat.loc[store_dates, 'date'].values,
        y_test.values[test_mask.values.nonzero()[0][X_test.index.isin(store_dates)]],
        y_pred[X_test.index.isin(store_dates)],
        alpha=0.15, color='gray'
    )
    axes[i].set_title(f'{store}——实际 vs 预测', fontsize=13, fontweight='bold')
    axes[i].set_ylabel('销售额', fontsize=11)
    axes[i].legend(loc='upper right')
    axes[i].grid(True, linestyle='--', alpha=0.4)

axes[2].set_xlabel('日期', fontsize=12)
plt.suptitle('多门店销售预测结果', fontsize=16, fontweight='bold', y=1.01)
plt.tight_layout()
```

### 8.4 综合案例4：客户流失预测

**业务背景**：SaaS企业需识别即将流失的客户，以便客户成功团队提前介入干预。

```python
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, f1_score, precision_recall_curve
import matplotlib.pyplot as plt
import shap

# ---- 模拟SaaS客户数据 ----
np.random.seed(42)
n = 3000

churn_df = pd.DataFrame({
    # 基础信息
    'tenure_months': np.random.exponential(24, n),                   # 使用月数
    'monthly_charge': np.random.lognormal(4, 0.5, n),               # 月费
    'total_charges': np.random.lognormal(8, 1, n) * np.random.uniform(0.5, 1.5, n),

    # 使用行为
    'login_freq_weekly': np.random.poisson(5, n),                    # 周登录次数
    'feature_usage_ratio': np.random.beta(2, 3, n),                 # 功能使用率
    'support_tickets': np.random.poisson(1.5, n),                    # 支持工单数
    'ticket_resolution_hours': np.random.exponential(24, n),         # 工单解决时长

    # 支付行为
    'payment_delays': np.random.poisson(0.8, n),                     # 延迟支付次数
    'contract_type': np.random.choice(['月度', '季度', '年度'], n,
                                       p=[0.40, 0.30, 0.30]),
    'discount_rate': np.random.beta(1.5, 4, n) * 0.5,               # 折扣率

    # 使用趋势
    'usage_trend': np.random.normal(0, 0.3, n),                      # 使用量趋势（负值=下滑）
    'recent_complaints': np.random.poisson(0.3, n),                  # 近期投诉数
})

# 模拟流失标签（流失≈15%）
churn_score = (
    -0.03 * churn_df['tenure_months']
    + 0.5 * churn_df['payment_delays']
    - 0.8 * churn_df['feature_usage_ratio']
    - 1.2 * churn_df['usage_trend']
    + 0.4 * np.log1p(churn_df['support_tickets'])
    + 0.6 * churn_df['recent_complaints']
    - 0.4 * (churn_df['contract_type'] == '年度').astype(int)
)
churn_prob = 1 / (1 + np.exp(-churn_score + 0.5 * np.random.randn(n)))
churn_df['churn'] = (churn_prob > np.percentile(churn_prob, 85)).astype(int)

print(f"流失率: {churn_df['churn'].mean():.1%}")

# ---- 数据预处理 ----
# 分类变量编码
churn_df = pd.get_dummies(churn_df, columns=['contract_type'], drop_first=False)

# 特征与标签
features = [c for c in churn_df.columns if c != 'churn']
X = churn_df[features]
y = churn_df['churn']

# ---- 建模对比 ----
models = {
    'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
    'Random Forest': RandomForestClassifier(n_estimators=200, max_depth=8,
                                             class_weight='balanced',
                                             random_state=42, n_jobs=-1),
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

for name, model in models.items():
    auc_scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
    print(f"{name}: AUC = {auc_scores.mean():.4f} ± {auc_scores.std():.4f}")

# ---- SHAP模型解释 ----
rf = RandomForestClassifier(n_estimators=200, max_depth=8,
                             class_weight='balanced', random_state=42)
rf.fit(X, y)

explainer = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X)

# SHAP摘要图
shap.summary_plot(shap_values[:, :, 1], X, feature_names=features,
                  max_display=10, show=False)
plt.title('客户流失特征SHAP摘要图', fontsize=14, fontweight='bold')

# ---- 流失风险评分 ----
y_proba = rf.predict_proba(X)[:, 1]
churn_df['churn_risk_score'] = y_proba

# 分风险等级
churn_df['risk_level'] = pd.cut(
    churn_df['churn_risk_score'],
    bins=[0, 0.3, 0.5, 0.7, 1.0],
    labels=['低风险', '中风险', '高风险', '极高风险'],
    right=True
)

print("\n=== 客户流失风险分布 ===")
print(churn_df['risk_level'].value_counts())

print("\n=== 高风险客户特征画像 ===")
high_risk = churn_df[churn_df['risk_level'].isin(['高风险', '极高风险'])]
for col in ['tenure_months', 'monthly_charge', 'feature_usage_ratio',
            'payment_delays', 'usage_trend', 'recent_complaints']:
    print(f"  {col}: 均值={high_risk[col].mean():.2f} "
          f"(全量均值={churn_df[col].mean():.2f})")

# ---- 业务建议 ----
print("""
=== 客户流失干预建议 ===
1. 极高风险客户（top 5%）：专属客户成功经理1对1沟通、定制化补救方案
2. 高风险客户（top 5-20%）：自动发送产品功能推荐、免费培训邀请
3. 使用量下滑但未投诉的客户：主动触达询问使用体验（沉默流失更危险）
4. 支付延迟+工单多的客户：可能是价格敏感型，考虑灵活定价方案
""")
```

### 8.5 数据分析完整工作流总结

```
┌─────────────────────────────────────────────────────────────────┐
│                    数据分析完整工作流                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 问题定义                                                      │
│     ├── 业务问题是什么？（提升转化率? 降低流失? 优化库存?）         │
│     ├── 成功指标是什么？（需要可量化可追踪的KPI）                   │
│     └── 数据可得性评估（有哪些数据? 质量如何? 能否采集?）           │
│                                                                 │
│  2. 数据获取与集成                                                │
│     ├── 从数据库/API/文件读取raw data                             │
│     ├── 多表关联与数据整合                                         │
│     └── 初步数据量级评估（行数、列数、存储）                        │
│                                                                 │
│  3. 数据探索（EDA）                                               │
│     ├── 结构探查：shape, dtypes, info, describe                   │
│     ├── 质量评估：缺失率、重复率、异常值                            │
│     ├── 单变量分析：分布形态、偏度峰度、分位数                      │
│     ├── 双变量分析：相关性、分组对比、交叉表                        │
│     └── 多变量分析：降维投影、分面可视化、聚类探查                   │
│                                                                 │
│  4. 数据清洗与特征工程                                             │
│     ├── 缺失值处理（填充/删除/模型填充）                            │
│     ├── 异常值处理（修正/截断/标记）                                │
│     ├── 特征编码（OHE/Ordinal/Target Encoding）                   │
│     ├── 特征缩放（Standard/MinMax/Robust）                        │
│     ├── 特征构建（组合/分解/业务规则）                              │
│     └── 特征选择（相关性/重要性/递归消除）                          │
│                                                                 │
│  5. 建模与分析                                                    │
│     ├── 基线模型（简单规则/均值预测）                               │
│     ├── 模型选择（线性→树模型→集成）                               │
│     ├── 交叉验证与超参数调优                                       │
│     ├── 模型评估（多指标综合判断）                                  │
│     └── 模型解释（特征重要性/SHAP/PDP）                            │
│                                                                 │
│  6. 结论与建议                                                    │
│     ├── 将统计指标翻译为业务语言                                    │
│     ├── 量化预期业务影响                                           │
│     ├── 识别关键驱动因素与可操作杠杆                                 │
│     └── 建议下一步行动（上线/更多数据/调整策略）                     │
│                                                                 │
│  7. 部署与监控                                                    │
│     ├── 模型部署（API/批处理/嵌入式）                               │
│     ├── 数据质量监控（漂移检测/异常告警）                            │
│     ├── 模型性能跟踪（衰减检测/定期重训练）                          │
│     └── A/B测试验证实际业务效果                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.6 常用数据分析工具链速查

| 环节 | 工具/库 | 核心用途 |
|------|---------|---------|
| 数据读取 | `pandas`, `sqlalchemy`, `openpyxl`, `pyarrow` | CSV/Excel/SQL/Parquet读写 |
| 数值计算 | `numpy`, `scipy` | 向量化运算、统计分布、优化求解 |
| 数据处理 | `pandas` | DataFrame操作、分组、透视、合并 |
| 可视化(静态) | `matplotlib`, `seaborn` | 出版级图表、统计可视化 |
| 可视化(交互) | `plotly`, `bokeh`, `altair` | 探索式可视化、仪表板 |
| 统计检验 | `scipy.stats`, `statsmodels` | 假设检验、回归诊断、时间序列分析 |
| 机器学习 | `scikit-learn`, `xgboost`, `lightgbm`, `catboost` | 分类、回归、聚类、降维 |
| 模型解释 | `shap`, `lime`, `eli5` | SHAP值、局部解释、排列重要性 |
| 报告生成 | `ydata-profiling`, `great_expectations` | 自动EDA报告、数据质量验证 |
| 工作流管理 | `jupyter`, `vscode`, `dvc` | 交互式分析、版本控制、实验追踪 |

---

> **编写说明**：本文档覆盖了Python数据分析从基础语法到高级应用的完整知识体系，包含8大章、超过50个小节、200+可运行代码示例。各章节既可顺序学习作为系统课程，也可按需查询作为速查手册。建议配合Jupyter Notebook环境边学边练，每个代码块都应在本地运行并观察输出结果。

> *文档最后更新：2024年 | 2025年增补：第9-14章高性能计算、时间序列、因果推断、数据质量、MLOps、可组合数据栈*

---

## 第9章 高性能计算与大数据处理

### 9.1 Polars —— 下一代高性能DataFrame库

Polars是用Rust语言编写的高性能DataFrame库，通过Apache Arrow内存格式实现零拷贝数据共享，在多核并行和延迟计算方面远超Pandas。

**核心优势**：
- **延迟计算（Lazy Evaluation）**：自动优化查询执行计划，只在必要时触发计算
- **多线程并行**：原生利用所有CPU核心
- **内存效率**：列式存储+零拷贝，内存占用比Pandas低30-50%
- **表达式API**：类型安全的链式操作，编译时即可发现错误

```python
import polars as pl

# ---- 创建DataFrame ----
df = pl.DataFrame({
    'name': ['张三', '李四', '王五', '赵六', '钱七'],
    'age': [25, 30, 35, 28, 42],
    'salary': [5000, 8000, 7500, 6000, 12000],
    'city': ['北京', '上海', '广州', '深圳', '北京'],
    'department': ['技术', '市场', '技术', '运营', '技术']
})

# ---- 表达式API（链式操作，类似data.table）----
result = (df
    .filter(pl.col('salary') > 6000)
    .group_by('city')
    .agg([
        pl.col('salary').mean().alias('平均薪资'),
        pl.col('salary').sum().alias('总薪资'),
        pl.col('name').count().alias('人数'),
        pl.col('age').max().alias('最大年龄')
    ])
    .sort('平均薪资', descending=True))
print(result)

# ---- 延迟计算（LazyFrame）----
# LazyFrame不会立即执行，而是构建查询计划
lazy_df = df.lazy()

# 复杂操作链（仅构建计划，不执行）
query = (lazy_df
    .filter(pl.col('age') > 25)
    .with_columns([
        (pl.col('salary') * 12).alias('年薪'),
        pl.when(pl.col('salary') > 7000).then(pl.lit('高')).otherwise(pl.lit('低')).alias('薪资等级')
    ])
    .group_by('department', '薪资等级')
    .agg([
        pl.col('年薪').mean().alias('平均年薪'),
        pl.count().alias('人数')
    ]))

# .collect()触发计算（此时才执行优化后的查询计划）
result = query.collect()
print(result)

# 查看优化后的查询计划
print(query.explain())

# ---- streaming模式（处理超出内存的大数据集）----
result = (pl.scan_csv('huge_file.csv')  # scan_*返回LazyFrame
    .filter(pl.col('amount') > 100)
    .group_by('category')
    .agg(pl.col('amount').sum())
    .collect(streaming=True))  # streaming=True表示流式处理，不在内存中聚合

# ---- 读取大文件 ----
# Polars读取速度是Pandas的10-30倍
df = pl.read_csv('large_data.csv',
                 infer_schema_length=10000,  # 推断schema的行数
                 null_values=['NA', 'N/A', 'null'],
                 try_parse_dates=True)

# 读取Parquet（Arrow原生格式，速度最快）
df = pl.read_parquet('data.parquet')
df.write_parquet('output.parquet', compression='zstd')

# ---- 窗口函数 ----
df.with_columns([
    pl.col('salary').rank('dense', descending=True).over('department').alias('部门内薪资排名'),
    (pl.col('salary') - pl.col('salary').mean().over('department')).alias('离部门均值差'),
    pl.col('salary').shift(1).over('department').alias('部门内前一行薪资'),
    pl.col('salary').rolling_mean(window_size=3).over('department').alias('滑动均值')
])
```

**性能对比**：读写10GB CSV时Polars约8秒，Pandas约3分钟；复杂groupby聚合时Polars约0.6秒，Pandas约12秒。

### 9.2 DuckDB —— 嵌入式OLAP数据库

DuckDB被称为"SQLite for analytics"，是一个嵌入式列式数据库引擎，可在Python进程中直接运行，无需配置服务器。

```python
import duckdb
import pandas as pd

# 连接（内存模式，无需服务器配置）
con = duckdb.connect(':memory:')
# 持久化模式
con = duckdb.connect('analytics.db')

# ---- 直接查询Pandas DataFrame ----
df = pd.DataFrame({'name': ['张三', '李四'], 'score': [85, 92]})
result = con.execute("SELECT * FROM df WHERE score > 80").df()
print(result)

# ---- 直接查询CSV/Parquet文件（无需预先加载）----
result = con.execute("""
    SELECT category, SUM(amount) AS total, COUNT(*) AS cnt
    FROM read_csv_auto('sales_*.csv')
    GROUP BY category
    ORDER BY total DESC
""").df()

# 查询Parquet（推荐格式，列式存储查询极快）
result = con.execute("""
    SELECT * FROM read_parquet('data/*.parquet')
    WHERE year = 2024
""").df()

# ---- SQL复杂分析（在Pandas中写SQL）----
query = """
WITH monthly_stats AS (
    SELECT
        DATE_TRUNC('month', date) AS month,
        category,
        SUM(amount) AS revenue,
        LAG(SUM(amount)) OVER (PARTITION BY category ORDER BY DATE_TRUNC('month', date)) AS prev_revenue
    FROM sales
    GROUP BY 1, 2
)
SELECT
    month, category, revenue,
    prev_revenue,
    (revenue - prev_revenue) / prev_revenue * 100 AS growth_pct,
    SUM(revenue) OVER (PARTITION BY category ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS rolling_3m_sum
FROM monthly_stats
ORDER BY category, month
"""
result = con.execute(query).df()

# ---- 创建表并写入 ----
con.execute("CREATE TABLE orders AS SELECT * FROM read_csv_auto('orders.csv')")
con.execute("INSERT INTO orders SELECT * FROM read_csv_auto('new_orders.csv')")

# ---- DuckDB与Pandas/Polars协作 ----
# DuckDB ↔ Pandas
df_pandas = con.execute("SELECT * FROM orders").df()
# DuckDB ↔ Polars
df_polars = con.execute("SELECT * FROM orders").pl()

# ---- 关闭连接 ----
con.close()
```

**核心场景**：本地大数据集（GB级）的SQL分析；替代Pandas做复杂聚合（SQL表达力更强）；作为轻量级分析数据库嵌入Python应用。

### 9.3 Dask —— 分布式Pandas

Dask让Pandas代码无缝扩展到分布式集群，API与Pandas高度兼容。

```python
import dask.dataframe as dd
from dask.distributed import Client

# ---- 启动分布式客户端（本地多核或集群）----
client = Client(n_workers=4, threads_per_worker=2)
print(client)

# ---- 读取大数据集（延迟加载）----
# 文件被自动分割为多个分区
df = dd.read_csv('data/*.csv',
                 parse_dates=['date'],
                 dtype={'user_id': 'int32'})

# 查看分区数
print(f"分区数: {df.npartitions}")

# ---- 操作与Pandas相同的API ----
# 以下代码不会立即执行，构建计算图
top_cities = (df[df['amount'] > 100]
              .groupby('city')
              .agg({'amount': ['sum', 'mean'], 'user_id': 'count'})
              .sort_values(('amount', 'sum'), ascending=False))

# .compute()触发实际计算
result = top_cities.compute()

# ---- Dask延迟函数 ----
from dask import delayed

@delayed
def load_and_clean(filepath):
    """每个文件独立清洗"""
    df = pd.read_csv(filepath)
    df = df.dropna(subset=['amount'])
    df['date'] = pd.to_datetime(df['date'])
    return df

file_list = ['data/sales_2024_Q1.csv', 'data/sales_2024_Q2.csv',
             'data/sales_2024_Q3.csv', 'data/sales_2024_Q4.csv']

# 并行执行
lazy_dfs = [load_and_clean(f) for f in file_list]
combined = delayed(pd.concat)(lazy_dfs)
result = combined.compute()

# ---- Dask DataFrame写入 ----
df.to_parquet('output/', partition_on=['year', 'month'])
# 目录结构: output/year=2024/month=01/part.0.parquet

# ---- 关闭客户端 ----
client.close()
```

### 9.4 其它大数据处理工具速查

| 工具 | 定位 | 核心场景 |
|------|------|---------|
| **Vaex** | 内存外DataFrame（惰性加载） | 百GB级交互式探索 |
| **Modin** | 一行代码加速Pandas | `import modin.pandas as pd`直接替换 |
| **PySpark** | 分布式大数据处理 | TB-PB级数据、与Spark生态集成 |
| **Ray** | 分布式计算框架 | 分布式训练、超参搜索、特征工程 |
| **Numba** | JIT编译器 | 加速纯Python数值计算循环 |

---

## 第10章 时间序列分析与预测

### 10.1 时间序列分解与平稳性检验

时间序列分析是数据分析中的关键技能，覆盖趋势分解、平稳性检验、自相关分析和模型构建。

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import seasonal_decompose, STL
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

# ---- 加载时间序列数据 ----
df = pd.read_csv('monthly_sales.csv', parse_dates=['date'], index_col='date')
series = df['sales'].asfreq('MS')  # 确保频率一致

# ---- 经典分解（additive: y = trend + seasonal + residual）----
decomposition = seasonal_decompose(series, model='additive', period=12)
fig, axes = plt.subplots(4, 1, figsize=(12, 10))
axes[0].plot(series, label='原始序列')
axes[1].plot(decomposition.trend, label='趋势', color='red')
axes[2].plot(decomposition.seasonal, label='季节性', color='green')
axes[3].plot(decomposition.resid, label='残差', color='gray')
for ax in axes:
    ax.legend(loc='upper left')
plt.tight_layout()

# ---- STL分解（更鲁棒，可处理变化的季节性）----
stl = STL(series, period=12, robust=True)
result = stl.fit()
fig = result.plot()
fig.set_size_inches(12, 8)
plt.tight_layout()

# ---- 平稳性检验 ----
# ADF检验（H₀: 存在单位根=非平稳）
adf_stat, adf_pvalue, _, _, critical_values, _ = adfuller(series.dropna())
print(f"ADF统计量: {adf_stat:.4f}, p值: {adf_pvalue:.4f}")
print(f"结论: {'平稳' if adf_pvalue < 0.05 else '非平稳'} (α=0.05)")

# KPSS检验（H₀: 序列平稳，与ADF互补使用）
kpss_stat, kpss_pvalue, _, critical_values = kpss(series.dropna())
print(f"KPSS统计量: {kpss_stat:.4f}, p值: {kpss_pvalue:.4f}")

# 如果非平稳：差分处理
series_diff = series.diff().dropna()

# ---- ACF/PACF图（确定ARIMA参数）----
fig, axes = plt.subplots(2, 1, figsize=(12, 8))
plot_acf(series.dropna(), lags=40, ax=axes[0])
axes[0].set_title('自相关函数(ACF)', fontsize=14)
plot_pacf(series.dropna(), lags=40, ax=axes[1])
axes[1].set_title('偏自相关函数(PACF)', fontsize=14)
plt.tight_layout()
```

### 10.2 ARIMA / SARIMA 模型

```python
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

# ---- 确定差分阶数d ----
d = 0
series_tmp = series.copy()
for _ in range(3):
    _, p_value, _, _, _, _ = adfuller(series_tmp.dropna())
    if p_value < 0.05:
        break
    series_tmp = series_tmp.diff().dropna()
    d += 1
print(f"差分阶数: d={d}")

# ---- ARIMA模型 ----
model = ARIMA(series, order=(2, d, 2))  # ARIMA(p, d, q)
fitted = model.fit()
print(fitted.summary())

# 残差诊断
fig = fitted.plot_diagnostics(figsize=(12, 8))

# 预测
forecast = fitted.forecast(steps=12)  # 预测未来12期
print(forecast)

# ---- SARIMA模型（含季节性）----
# SARIMA(p,d,q)(P,D,Q)s，s=12表示年周期（月度数据）
sarima = SARIMAX(series,
                 order=(2, 1, 2),
                 seasonal_order=(1, 1, 1, 12),
                 enforce_stationarity=False,
                 enforce_invertibility=False)
sarima_fitted = sarima.fit()
print(sarima_fitted.summary())

# 预测 + 置信区间
forecast_result = sarima_fitted.get_forecast(steps=12)
forecast_df = forecast_result.conf_int()
forecast_df['预测值'] = forecast_result.predicted_mean
forecast_df.columns = ['下界', '上界', '预测值']

# 可视化
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(series.index, series, 'b-', label='历史数据', alpha=0.7)
ax.plot(forecast_df.index, forecast_df['预测值'], 'r--', label='预测值', linewidth=2)
ax.fill_between(forecast_df.index, forecast_df['下界'], forecast_df['上界'],
                color='red', alpha=0.15, label='95%置信区间')
ax.legend()
ax.set_title('SARIMA时间序列预测', fontsize=14, fontweight='bold')
ax.grid(True, linestyle='--', alpha=0.4)

# ---- 模型选择（grid search AIC）----
import itertools

best_aic = np.inf
best_order = None

p = d = q = range(0, 3)
pdq_combinations = list(itertools.product(p, d, q))
seasonal_pdq = [(x[0], x[1], x[2], 12) for x in list(itertools.product(p, d, q))]

for order in pdq_combinations:
    for seasonal_order in seasonal_pdq:
        try:
            model = SARIMAX(series, order=order, seasonal_order=seasonal_order)
            result = model.fit()
            if result.aic < best_aic:
                best_aic = result.aic
                best_order = (order, seasonal_order)
        except:
            continue

print(f"最佳AIC: {best_aic:.2f}")
print(f"最佳参数: SARIMA{best_order[0]}x{best_order[1]}")
```

### 10.3 Prophet —— 业务预测利器

Prophet由Meta（原Facebook）开发，专为业务时间序列设计，对缺失值、趋势突变、节假日效应都有很好的鲁棒性。

```python
from prophet import Prophet
import pandas as pd
import matplotlib.pyplot as plt

# ---- 准备数据（Prophet要求列名ds和y）----
df_prophet = pd.DataFrame({
    'ds': series.index,
    'y': series.values
})

# ---- 创建并拟合模型 ----
model = Prophet(
    growth='linear',            # 'linear' 或 'logistic'（需要设置cap上限）
    yearly_seasonality=True,    # 年周期
    weekly_seasonality=False,   # 月数据无需周周期
    daily_seasonality=False,
    seasonality_mode='additive', # 'additive' 或 'multiplicative'
    changepoint_prior_scale=0.05, # 趋势变化敏感度（越大越灵活）
    seasonality_prior_scale=10.0, # 季节性强度（越大越灵活）
    holidays_prior_scale=10.0,
    interval_width=0.95          # 置信区间宽度
)

# ---- 添加节假日 ----
holidays = pd.DataFrame({
    'holiday': '双十一',
    'ds': pd.to_datetime(['2023-11-11', '2024-11-11']),
    'lower_window': 0,
    'upper_window': 3  # 延长影响3天
})
model.add_country_holidays(country_name='CN')  # 自动添加中国节日
model = Prophet(holidays=holidays)

model.fit(df_prophet)

# ---- 预测 ----
future = model.make_future_dataframe(periods=12, freq='MS')  # 未来12个月
forecast = model.predict(future)

# ---- 可视化 ----
# 整体预测
fig1 = model.plot(forecast)
fig1.set_size_inches(14, 6)

# 分解（趋势+季节性）
fig2 = model.plot_components(forecast)
fig2.set_size_inches(12, 8)

# 交叉验证
from prophet.diagnostics import cross_validation, performance_metrics
df_cv = cross_validation(model, initial='365 days', period='180 days', horizon='365 days')
df_pm = performance_metrics(df_cv)
print(df_pm[['horizon', 'mape', 'rmse']].head(10))
fig3 = plot_cross_validation_metric(df_cv, metric='mape')
```

### 10.4 指数平滑法（Exponential Smoothing）

```python
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing

# ---- 简单指数平滑（无趋势无季节）----
ses = SimpleExpSmoothing(series).fit(smoothing_level=0.2, optimized=True)
ses_forecast = ses.forecast(12)

# ---- Holt双指数平滑（有趋势无季节）----
holt = ExponentialSmoothing(series, trend='add').fit(optimized=True)
holt_forecast = holt.forecast(12)

# ---- Holt-Winters三指数平滑（有趋势有季节）----
# additive适用于季节性幅度不变
hw_add = ExponentialSmoothing(series,
                              trend='add',
                              seasonal='add',
                              seasonal_periods=12).fit(optimized=True)
# multiplicative适用于季节性幅度随趋势增大
hw_mul = ExponentialSmoothing(series,
                              trend='mul',
                              seasonal='mul',
                              seasonal_periods=12).fit(optimized=True)

# ---- 预测对比 ----
fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(series.index, series, 'k-', label='历史数据', alpha=0.7)
ax.plot(holt_forecast.index, holt_forecast, 'b--', label='Holt', linewidth=2)
ax.plot(hw_add_forecast.index, hw_add_forecast, 'r--', label='Holt-Winters(add)', linewidth=2)
ax.plot(hw_mul_forecast.index, hw_mul_forecast, 'g--', label='Holt-Winters(mul)', linewidth=2)
ax.legend()
ax.set_title('指数平滑模型对比', fontsize=14, fontweight='bold')
ax.grid(True, linestyle='--', alpha=0.4)
```

### 10.5 时间序列预测评估

```python
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np

def forecast_evaluation(y_true, y_pred):
    """完整的时间序列预测评估"""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    smape = 200 * np.mean(np.abs(y_true - y_pred) / (np.abs(y_true) + np.abs(y_pred)))

    # 均值偏差（判断系统性高估/低估）
    mbe = np.mean(y_pred - y_true)

    return pd.DataFrame({
        '指标': ['MAE', 'RMSE', 'MAPE(%)', 'sMAPE(%)', '均值偏差'],
        '值': [mae, rmse, mape, smape, mbe]
    })

# ---- 回溯测试（Backtesting）----
def walk_forward_validation(series, model_func, train_window=36, forecast_horizon=1):
    """滚动时间窗口验证"""
    predictions = []
    actuals = []

    for i in range(train_window, len(series) - forecast_horizon + 1):
        train = series.iloc[:i]
        test = series.iloc[i:i+forecast_horizon]

        model = model_func(train)
        forecast = model.forecast(forecast_horizon)

        predictions.extend(forecast)
        actuals.extend(test.values)

    return np.array(actuals), np.array(predictions)
```

---

## 第11章 因果推断

### 11.1 因果推断概述

**相关性≠因果性**。因果推断致力于回答"如果做X，Y会怎么变"的反事实问题。

**核心方法体系**：

| 方法 | 适用场景 | 核心思想 | 工具 |
|------|---------|---------|------|
| A/B测试（RCT） | 可随机分配实验 | 随机化消除混淆 | `scipy.stats` |
| 双重差分（DiD） | 平行趋势成立 | 比较处理组与对照组的前后差异 | `statsmodels` |
| 倾向性得分匹配（PSM） | 有混淆变量的观测数据 | 按倾向性得分匹配相似样本 | `causalmatch` |
| 工具变量（IV） | 存在未观测混淆 | 利用工具变量分离因果效应 | `linearmodels` |
| 断点回归（RDD） | 有明确截断规则 | 利用断点附近的局部随机性 | `rdrobust` |
| 因果森林 | 异质性处理效应 | 用树模型估计条件处理效应 | `econml` |

### 11.2 DoWhy —— 端到端因果推断框架

DoWhy由微软研究院开发，将因果推断分为建模(建模)、识别(识别)、估计(估计)、反驳(反驳)四个标准步骤。

```python
import dowhy
from dowhy import CausalModel
import pandas as pd
import numpy as np

# ---- 模拟因果推断数据 ----
np.random.seed(42)
n = 1000
X = np.random.normal(0, 1, n)         # 混淆变量
T = (0.3 * X + np.random.normal(0, 0.5, n)) > 0  # 处理（受X影响）
Y = 2.0 * T + 1.5 * X + np.random.normal(0, 1, n)  # 结果（T和X都影响）

df_causal = pd.DataFrame({'X': X, 'T': T.astype(int), 'Y': Y})

# ---- 步骤1：建模 ----
model = CausalModel(
    data=df_causal,
    treatment='T',
    outcome='Y',
    graph="digraph { X -> T; X -> Y; T -> Y; }"  # 因果图(DAG)
)

# 可视化因果图
model.view_model()

# ---- 步骤2：识别（找出因果效应的估计策略）----
identified_estimand = model.identify_effect()
print(identified_estimand)

# ---- 步骤3：估计（使用具体估计方法）----
# 方法1：后门调整（基于因果图）
estimate = model.estimate_effect(
    identified_estimand,
    method_name='backdoor.linear_regression',
    control_value=0,    # 未处理
    treatment_value=1   # 处理
)
print(f"因果效应估计: {estimate.value:.4f}")

# 方法2：倾向性得分匹配
estimate_psm = model.estimate_effect(
    identified_estimand,
    method_name='backdoor.propensity_score_matching'
)
print(f"PSM因果效应: {estimate_psm.value:.4f}")

# 方法3：逆概率加权
estimate_ipw = model.estimate_effect(
    identified_estimand,
    method_name='backdoor.propensity_score_weighting'
)

# ---- 步骤4：反驳（检验假设的稳健性）----
# 随机洗牌处理变量（如果因果模型正确，效应应消失）
refute_random = model.refute_estimate(
    identified_estimand, estimate,
    method_name='random_common_cause'
)
print(f"安慰剂检验p值: {refute_random.new_effect:.4f}")

# 添加随机混淆变量（检验稳健性）
refute_unobserved = model.refute_estimate(
    identified_estimand, estimate,
    method_name='add_unobserved_common_cause'
)

# 使用数据子集重复（检验稳定性）
refute_subset = model.refute_estimate(
    identified_estimand, estimate,
    method_name='data_subset_refuter', subset_fraction=0.8
)
```

### 11.3 倾向性得分匹配（PSM）

```python
from causalmatch import matching

# ---- 使用causalmatch进行PSM ----
match_obj = matching(
    data=df_causal,
    T='T',        # 处理变量
    X=['X'],      # 协变量
    y='Y',        # 结果变量
    id='index'
)

# PSM匹配
match_obj.psm(
    n_neighbors=1,                      # 1:1匹配
    model=LogisticRegression(C=1e6),    # 倾向性得分模型
    caliper=0.2                         # 卡钳值（匹配容差）
)

# 平衡性检验（匹配后协变量应无显著差异）
balance = match_obj.balance_check(include_discrete=True)
print(balance)

# 计算平均处理效应（ATE）
ate = match_obj.ate()
print(f"ATE (匹配后): {ate}")

# 异质性处理效应
hte = match_obj.hte()
```

### 11.4 Causal Impact —— 策略效果评估

Causal Impact用于评估某个干预（如营销活动、策略变更）的时间序列效果。

```python
from causalimpact import CausalImpact
import pandas as pd

# ---- 准备数据 ----
df_ci = pd.DataFrame({
    'y': sales_data,          # 目标指标（处理组）
    'x1': control_sales_1,    # 对照组指标（用于构建反事实）
    'x2': control_sales_2
})

# 定义干预前后时间段
pre_period = ['2024-01-01', '2024-06-30']   # 干预前
post_period = ['2024-07-01', '2024-09-30']  # 干预后

# ---- 执行Causal Impact分析 ----
ci = CausalImpact(df_ci, pre_period, post_period)

# 结果报告
print(ci.summary())
print(ci.summary(output='report'))

# 可视化
ci.plot()

# 提取效应
summary = ci.summary_data
print(f"实际值: {summary['actual']['average']:.2f}")
print(f"预测值(反事实): {summary['predicted']['average']:.2f}")
print(f"因果效应: {summary['abs_effect']['average']:.2f}")
print(f"相对效应: {summary['rel_effect']['average']*100:.2f}%")
```

### 11.5 双重差分（Difference-in-Differences）

```python
import statsmodels.formula.api as smf
import pandas as pd
import numpy as np

# ---- 模拟DID数据 ----
np.random.seed(42)
df_did = pd.DataFrame({
    'id': np.repeat(range(100), 2),
    'time': np.tile([0, 1], 100),            # 0=干预前, 1=干预后
    'treated': np.repeat(np.random.binomial(1, 0.5, 100), 2),  # 是否处理组
    'y': np.random.normal(100, 10, 200) +      # 基线
         np.tile(np.random.normal(5, 2, 100), 2) * np.tile([0, 1], 100) +  # 时间趋势
         np.repeat(np.random.normal(10, 3, 100), 2) * np.tile([0, 1], 100) * np.repeat(np.random.binomial(1, 0.5, 100), 2)  # 处理效应
})

df_did['treated_time'] = df_did['treated'] * df_did['time']

# ---- DID回归 ----
model = smf.ols('y ~ treated + time + treated_time', data=df_did).fit()
print(model.summary())
print(f"\nDID因果效应: {model.params['treated_time']:.4f} (p={model.pvalues['treated_time']:.4f})")

# ---- DID平行趋势检验 ----
# 绘制处理组与对照组的时间趋势
import matplotlib.pyplot as plt
df_did.groupby(['treated', 'time'])['y'].mean().unstack().T.plot()
plt.axvline(x=0.5, color='red', linestyle='--', label='干预时间点')
plt.ylabel('结果变量')
plt.legend()
plt.title('平行趋势检验', fontsize=14, fontweight='bold')
```

---

## 第12章 数据质量与验证体系

### 12.1 Pandera —— DataFrame模式验证

Pandera让你像定义数据库Schema一样定义DataFrame的数据契约，在数据流入管道时自动验证结构和值。

```python
import pandera as pa
from pandera import Column, DataFrameSchema, Check, Index
from pandera.typing import DataFrame, Series
import pandas as pd

# ---- 定义Schema ----
sales_schema = DataFrameSchema(
    columns={
        'order_id': Column(int, Check.isin(range(1, 1000000)), nullable=False),
        'product': Column(str, Check.isin(['电子产品', '服装', '食品', '家居', '图书'])),
        'quantity': Column(int, Check.in_range(1, 1000)),
        'unit_price': Column(float, Check.greater_than(0), Check.less_than(100000)),
        'date': Column(pa.DateTime, Check(lambda d: d.dt.year >= 2020)),
        'customer_id': Column(str, Check.str_matches(r'^C\d{6}$'), nullable=True),
    },
    index=Index(int, name='row_id'),
    coerce=True,        # 自动类型转换
    strict=False,       # True=报错于额外列，False=允许额外列
    ordered=True        # 强制列顺序
)

# ---- 验证DataFrame ----
df = pd.read_csv('sales.csv')

try:
    validated_df = sales_schema.validate(df)
except pa.errors.SchemaError as e:
    print(f"Schema校验失败:\n{e}")

# ---- 在函数签名中使用装饰器 ----
@pa.check_input(sales_schema)
@pa.check_output(sales_schema)
def clean_sales(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=['product', 'price'])
    df['quantity'] = df['quantity'].clip(lower=1)
    return df

# ---- 定义输出Schema ----
output_schema = DataFrameSchema({
    'product': Column(str),
    'total_sales': Column(float, Check.greater_than(0)),
    'avg_price': Column(float),
    'order_count': Column(int)
})

@pa.check_output(output_schema)
def aggregate_sales(df):
    return df.groupby('product').agg(
        total_sales=('unit_price', lambda x: (x * df.loc[x.index, 'quantity']).sum()),
        avg_price=('unit_price', 'mean'),
        order_count=('order_id', 'count')
    ).reset_index()

# ---- 统计检查 ----
stat_schema = DataFrameSchema({
    'price': Column(float, [
        Check.greater_than(0),
        Check(lambda s: s.mean() > 10),      # 均值>10
        Check(lambda s: s.std() < s.mean()), # 标准差<均值
        Check(lambda s: s.isna().mean() < 0.05)  # 缺失率<5%
    ])
})

# ---- 自定义Check ----
from typing import Optional

def check_no_negative_totals(data: pd.DataFrame) -> pd.DataFrame:
    if (data['quantity'] * data['unit_price'] < 0).any():
        raise pa.errors.SchemaError("存在负的总金额")
    return data

@pa.check_input(sales_schema)
@pa.check_output(sales_schema, custom_check=check_no_negative_totals)
def process_sales(df):
    return df
```

### 12.2 Great Expectations —— 企业级数据质量

Great Expectations提供声明式的数据质量期望定义、自动文档生成和持续验证。

```python
import great_expectations as gx
from great_expectations.core import ExpectationSuite

# ---- 创建数据上下文 ----
context = gx.get_context(mode='file')  # 持久化模式

# ---- 连接数据源 ----
validator = context.sources.pandas_default.read_csv(
    'sales.csv'
)

# ---- 定义期望（Expectations）----
# 表级期望
validator.expect_table_row_count_to_be_between(min_value=100, max_value=1000000)
validator.expect_table_columns_to_match_ordered_list([
    'order_id', 'product', 'quantity', 'unit_price', 'date'
])

# 列级期望 —— 存在性与类型
validator.expect_column_to_exist('order_id')
validator.expect_column_values_to_not_be_null('order_id')
validator.expect_column_values_to_be_unique('order_id')
validator.expect_column_values_to_be_of_type('quantity', 'int64')

# 列级期望 —— 值范围与集合
validator.expect_column_values_to_be_in_set('product', [
    '电子产品', '服装', '食品', '家居', '图书'
])
validator.expect_column_values_to_be_between('quantity', min_value=1, max_value=1000)
validator.expect_column_values_to_be_between('unit_price', min_value=0.01, max_value=50000)

# 列级期望 —— 统计属性
validator.expect_column_mean_to_be_between('unit_price', min_value=10, max_value=10000)
validator.expect_column_unique_value_count_to_be_between('product', min_value=1, max_value=50)
validator.expect_column_proportion_of_unique_values_to_be_between('order_id', min_value=0.95)
validator.expect_column_values_to_match_regex('customer_id', r'^C\d{6}$')

# 列级期望 —— 分布（与参考数据对比）
validator.expect_column_kl_divergence_to_be_less_than('unit_price',
    partition_object={'bins': [0, 100, 500, 1000, 5000, 50000],
                      'weights': [0.1, 0.2, 0.3, 0.3, 0.1]},
    threshold=0.1)

# ---- 保存期望套件 ----
validator.save_expectation_suite(discard_failed_expectations=False)

# ---- 生成数据文档 ----
checkpoint = gx.checkpoint.SimpleCheckpoint(
    name='sales_validation',
    data_context=context,
    validator=validator
)
checkpoint_result = checkpoint.run()

# 转为HTML报告
context.build_data_docs()
```

### 12.3 Pydantic —— 类型安全的配置管理

Pydantic利用Python类型提示实现运行时数据验证，广泛用于API输入验证和配置管理。

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional, List, Literal

# ---- 定义数据模型 ----
class SalesRecord(BaseModel):
    order_id: int = Field(..., gt=0, description='订单ID')
    product: str = Field(..., min_length=1, max_length=50)
    quantity: int = Field(..., ge=1, le=1000)
    unit_price: float = Field(..., gt=0)
    date: datetime

    @field_validator('product')
    @classmethod
    def product_must_be_valid(cls, v):
        allowed = ['电子产品', '服装', '食品', '家居', '图书']
        if v not in allowed:
            raise ValueError(f'产品必须在 {allowed} 中')
        return v

    @model_validator(mode='after')
    def check_total_amount(self):
        if self.quantity * self.unit_price > 1000000:
            raise ValueError('订单总金额不得超过100万')
        return self

# ---- 配置管理 ----
class AnalysisConfig(BaseModel):
    input_file: str = Field(..., description='输入数据文件路径')
    output_dir: str = Field('output', description='输出目录')
    date_range: tuple[datetime, datetime]
    min_sample_size: int = Field(100, ge=10)
    confidence_level: float = Field(0.95, ge=0.8, le=0.999)
    features: List[str]
    model_type: Literal['rf', 'lr', 'xgb', 'lgb'] = 'rf'
    random_state: int = 42

    @field_validator('features')
    @classmethod
    def features_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError('特征列表不能为空')
        return v

# 使用时从YAML/JSON/dict解析
config = AnalysisConfig(
    input_file='data/sales.csv',
    date_range=(datetime(2024, 1, 1), datetime(2024, 12, 31)),
    features=['price', 'quantity', 'day_of_week', 'is_weekend']
)
print(config.model_dump_json(indent=2))
```

---

## 第13章 MLOps与实验管理

### 13.1 MLflow —— 实验追踪与模型注册

MLflow是管理端到端机器学习生命周期的开源平台，包含实验追踪、模型注册、模型部署和模型评估四个组件。

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

# ---- 设置 ----
mlflow.set_tracking_uri('sqlite:///mlflow.db')   # 追踪服务器地址
mlflow.set_experiment('churn_prediction')         # 实验名称

# ---- 记录实验 ----
params_list = [
    {'n_estimators': 100, 'max_depth': 5, 'min_samples_leaf': 2},
    {'n_estimators': 200, 'max_depth': 8, 'min_samples_leaf': 4},
    {'n_estimators': 300, 'max_depth': 10, 'min_samples_leaf': 1},
]

for i, params in enumerate(params_list):
    with mlflow.start_run(run_name=f'RF_run_{i+1}'):
        # 记录参数
        mlflow.log_params(params)

        # 训练模型
        model = RandomForestClassifier(**params, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        # 预测与评估
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)

        # 记录指标
        mlflow.log_metrics({
            'accuracy': acc,
            'f1_score': f1,
            'roc_auc': auc
        })

        # 记录模型（自动记录conda环境和依赖）
        mlflow.sklearn.log_model(
            model, 'model',
            registered_model_name='churn_rf'
        )

        # 记录特征重要性
        importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': model.feature_importances_
        }).to_dict('records')
        mlflow.log_dict(importance, 'feature_importance.json')

        # 记录图表
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(data=pd.DataFrame(importance).head(10),
                     y='feature', x='importance', ax=ax)
        mlflow.log_figure(fig, 'feature_importance.png')

# ---- 加载已注册模型 ----
logged_model = 'models:/churn_rf/Production'
loaded_model = mlflow.pyfunc.load_model(logged_model)
predictions = loaded_model.predict(X_new)

# ---- MLflow自动记录（一行代码）----
mlflow.sklearn.autolog(log_models=True, log_datasets=True)
model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)  # 自动记录所有参数/指标/模型

# 启动MLflow UI（终端命令）
# mlflow ui --backend-store-uri sqlite:///mlflow.db
```

### 13.2 特征存储与管道管理

```python
# ---- 使用Kedro管道管理数据工程流程 ----
# Kedro项目结构:
# project/
#   conf/base/catalog.yml   # 数据目录
#   src/pipelines/          # 管道定义
#   notebooks/              # Jupyter notebooks

# catalog.yml 示例
"""
raw_sales:
  type: pandas.CSVDataset
  filepath: data/01_raw/sales.csv

cleaned_sales:
  type: pandas.ParquetDataset
  filepath: data/02_intermediate/cleaned_sales.parquet

feature_table:
  type: pandas.ParquetDataset
  filepath: data/04_feature/feature_table.parquet
"""

# ---- 管道节点定义 ----
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """数据清洗节点"""
    df = df.dropna(subset=['amount'])
    df['date'] = pd.to_datetime(df['date'])
    return df

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """特征工程节点"""
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['month'] = df['date'].dt.month
    return df

# ---- 管道类 ----
from kedro.pipeline import Pipeline, node

pipeline = Pipeline([
    node(func=clean_data, inputs='raw_sales', outputs='cleaned_sales'),
    node(func=create_features, inputs='cleaned_sales', outputs='feature_table'),
])

# 执行: kedro run --pipeline=my_pipeline
```

### 13.3 模型监控与漂移检测

```python
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
from evidently.test_suite import TestSuite
from evidently.tests import TestColumnDrift

# ---- 数据漂移检测 ----
column_mapping = ColumnMapping(
    target='churn',
    numerical_features=['age', 'income', 'tenure_months', 'usage_ratio'],
    categorical_features=['city', 'contract_type'],
    datetime='date'
)

# 生成数据漂移报告
report = Report(metrics=[
    DataDriftPreset(),
    TargetDriftPreset(),
])
report.run(reference_data=df_train, current_data=df_prod,
           column_mapping=column_mapping)
report.save_html('drift_report.html')

# ---- 自动化漂移测试 ----
test_suite = TestSuite(tests=[
    TestColumnDrift(column_name='income'),
    TestColumnDrift(column_name='usage_ratio'),
])
test_suite.run(reference_data=df_train, current_data=df_prod,
               column_mapping=column_mapping)

# 结果判断
if test_suite.as_dict()['summary']['failed_tests'] > 0:
    print("⚠️ 数据漂移告警！需检查或重训练模型")
```

---

## 第14章 可组合数据栈与未来趋势

### 14.1 Ibis —— 可移植的DataFrame API

Ibis提供统一的Python DataFrame接口，可编译到20+种后端引擎（DuckDB、Polars、PostgreSQL、BigQuery、Snowflake等），实现"一次编写，处处运行"。

```python
import ibis
from ibis import _

# ---- 连接DuckDB后端 ----
con = ibis.duckdb.connect()

# ---- 加载数据 ----
t = con.read_csv('sales.csv', table_name='sales')

# ---- 链式操作（Ibis延迟执行，编译为后端原生SQL）----
expr = (t
    .filter(_.amount > 100)
    .mutate(year=_.date.year(), month=_.date.month())
    .group_by(['year', 'month', 'category'])
    .agg(
        total_revenue=_.amount.sum(),
        avg_price=_.unit_price.mean(),
        order_count=_.id.count()
    )
    .order_by(_.total_revenue.desc())
)

# 查看编译后的SQL
print(ibis.to_sql(expr))
# SELECT
#   year, month, category,
#   SUM(amount) AS total_revenue,
#   AVG(unit_price) AS avg_price,
#   COUNT(id) AS order_count
# FROM sales
# WHERE amount > 100
# GROUP BY year, month, category
# ORDER BY total_revenue DESC

# 执行
result = expr.execute()
print(result)

# ---- 切换到Polars后端（无需修改代码！）----
con_polars = ibis.polars.connect()
t2 = con_polars.read_csv('sales.csv')
# 相同表达式，运行在Polars引擎上
result2 = expr.execute()  # 自动编译到Polars表达式

# ---- 生产环境切换到BigQuery ----
# con_bq = ibis.bigquery.connect(project_id='my-project', dataset_id='analytics')
# 完全相同的代码，现在运行在BigQuery上
```

### 14.2 Python 3.12/3.13 对数据分析的提升

```python
# Python 3.12+ 新增特性
# 1. 更好的错误消息（数据分析调试神器）
# 当你键入 df['salary'] 而 'salary' 不存在时：
# KeyError: 'salary' -> 现在会自动建议: "Did you mean 'Salary'?"

# 2. PEP 701: f-string语法增强（更灵活的字符串模板）
query = f"""
SELECT {', '.join(columns)}
FROM {table_name}
WHERE {' AND '.join(f"{col} > @{col}_threshold" for col in filter_cols)}
"""  # 现在支持嵌套f-string和转义

# 3. Python 3.13: 性能提升
# 无需修改代码，平均执行速度提升5-15%
# 内存占用降低约20-30%

# 4. 自由线程（3.13实验性）
# 移除GIL限制，NumPy/Pandas多线程性能大幅提升
```

### 14.3 包管理与项目管理现代化

```python
# ---- uv：新一代Python包管理工具（Rust实现，极速）----
# 安装uv: pip install uv  # 或 curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建项目 (替代 pip + virtualenv + pip-tools)
# uv init my_project     # 创建项目骨架（含pyproject.toml）
# uv add pandas numpy matplotlib  # 添加依赖（比pip快10-100倍）
# uv sync                 # 同步安装所有依赖
# uv run python script.py # 在项目环境中运行脚本

# pyproject.toml示例
"""
[project]
name = "sales-analysis"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pandas>=2.2.0",
    "polars>=1.0.0",
    "duckdb>=1.0.0",
    "matplotlib>=3.8.0",
    "scikit-learn>=1.5.0",
    "mlflow>=3.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
"""
```

### 14.4 数据分析核心趋势总结（2025）

| 趋势 | 说明 | 影响 |
|------|------|------|
| **Pandas 2.x Arrow后端** | 底层可选Apache Arrow作为内存格式 | 更快I/O、更好互操作性、更优类型系统 |
| **Polars成为新默认** | 高性能Rust引擎替代Pandas | 大数据集处理速度提升10-30倍 |
| **DuckDB嵌入式分析** | 本地OLAP数据库嵌入Python进程 | SQL+Python无缝融合，替代复杂Pandas操作 |
| **Ibis可移植API** | 统一DataFrame接口编译到20+后端 | 本地代码直接上线到大数据平台 |
| **因果推断普及** | 从"有相关性"到"有因果效应" | 更科学的AB测试分析和策略评估 |
| **数据质量工程化** | Pandera、Great Expectations成为标准 | 数据管道从"崩溃后修复"到"预防性验证" |
| **MLOps标准化** | MLflow提供实验→注册→部署全链路 | 模型管理从"笔记本散落"到"资产化" |
| **Python 3.13性能飞跃** | JIT编译器和自由线程(GIL-free) | 无需改写代码即可获10-50%性能提升 |
| **Parquet成为通用格式** | 列式存储成为数据分析标准交换格式 | 读写速度比CSV快10-100倍，存储体积减半 |
| **声明式分析管道** | Kedro/dbt/Prefect等框架 | 分析代码从"脚本"演进为"工程化管道" |

### 14.5 更新后的数据分析完整工作流

```
┌─────────────────────────────────────────────────────────────────────────┐
│               Python数据分析工作流（2025增强版）                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. 问题定义                                                             │
│     └── 因果问题？→ 设计因果图(DAG) → DoWhy/EconML                       │
│                                                                         │
│  2. 数据获取                                                             │
│     ├── 小数据(＜1GB): Pandas / Polars                                  │
│     ├── 中数据(1-100GB): DuckDB / Polars steaming                        │
│     └── 大数据(＞100GB): Dask / PySpark / Vaex                          │
│                                                                         │
│  3. 数据质量验证 ← 🆕                                                    │
│     ├── Schema验证: Pandera / Great Expectations                        │
│     ├── 配置管理: Pydantic                                              │
│     └── 漂移检测: Evidently AI / Deepchecks                             │
│                                                                         │
│  4. EDA与探索                                                             │
│     ├── 统计可视化: Matplotlib + Seaborn                                │
│     ├── 交互探索: Plotly / Altair                                       │
│     └── SQL探索: DuckDB → SQL查询DataFrame                              │
│                                                                         │
│  5. 数据清洗与特征工程                                                    │
│     └── 管道化: sklearn Pipeline / feature-engine                       │
│                                                                         │
│  6. 建模与分析                                                            │
│     ├── 时间序列 ← 🆕: Prophet / ARIMA / SARIMA / Holt-Winters         │
│     ├── 因果推断 ← 🆕: DoWhy / CausalMatch / 双重差分                   │
│     ├── 机器学习: scikit-learn + XGBoost + LightGBM                     │
│     └── AutoML ← 🆕: FLAML / PyCaret / AutoGluon                       │
│                                                                         │
│  7. 实验管理 ← 🆕                                                        │
│     └── MLflow → 实验追踪 + 模型注册 + 部署                              │
│                                                                         │
│  8. 结论与建议                                                            │
│     ├── 模型解释: SHAP → 特征重要性 + 个体解释                           │
│     └── 因果解读: 是相关性还是因果？                                      │
│                                                                         │
│  9. 部署与监控 ← 🆕                                                       │
│     ├── 数据漂移监控: Evidently AI                                       │
│     ├── 模型性能衰退: 定期重训练                                         │
│     └── 管道编排: Dagster / Prefect / Airflow                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 14.6 完整工具链速查表（2025增强版）

| 环节 | 工具/库 | 核心用途 |
|------|---------|---------|
| 数据读取(小) | `pandas`, `polars` | CSV/Excel/JSON读写 |
| 数据读取(大) | `duckdb`, `ibis` | 本地OLAP、SQL-on-DataFrame |
| 数据读取(分布式) | `dask`, `pyspark`, `vaex` | 集群/内存外大数据 |
| 数值计算(CPU) | `numpy`, `numba` | 向量化运算、JIT加速 |
| 数值计算(GPU) | `cupy`, `jax` | GPU加速数值运算 |
| 数据质量 | `pandera`, `great_expectations`, `pydantic` | Schema验证、数据契约 |
| 可视化(静态) | `matplotlib`, `seaborn` | 出版级图表发布 |
| 可视化(交互) | `plotly`, `altair`, `bokeh` | 探索式可视化 |
| 统计推断 | `scipy.stats`, `statsmodels` | 假设检验、回归诊断 |
| 时间序列 | `prophet`, `statsmodels`(SARIMA), `sktime` | 趋势预测、季节性建模 |
| 因果推断 | `dowhy`, `econml`, `causalmatch` | 策略效果评估、反事实分析 |
| 机器学习 | `scikit-learn`, `xgboost`, `lightgbm`, `catboost` | 分类、回归、聚类 |
| 模型解释 | `shap`, `lime`, `eli5` | 特征重要性、个体解释 |
| 实验管理 | `mlflow`, `wandb` | 实验追踪、模型注册 |
| 管道编排 | `kedro`, `dagster`, `prefect`, `airflow` | 生产级管道调度 |
| 数据漂移 | `evidently`, `deepchecks` | 监控数据/模型漂移 |
| 自动化报告 | `ydata-profiling`, `sweetviz` | 自动EDA报告生成 |
| 包管理 | `uv`, `poetry`, `conda` | 依赖管理、环境复用 |
| 数据格式 | `pyarrow`, `parquet`, `orc` | 高性能列式存储 |

---

> **更新说明（2025年第一版）**：本文档第9-14章为2025年增补内容，新增Polars高性能计算、DuckDB嵌入式分析、时间序列预测（Prophet/ARIMA/SARIMA）、因果推断（DoWhy/PSM/DID/CausalImpact）、数据质量验证体系（Pandera/Great Expectations/Pydantic）、MLOps实验管理（MLflow/Kedro/漂移检测）、可组合数据栈（Ibis）及行业趋势等约200个代码示例。

---

## 第15章 Python数据工程基础

> 真实工作的数据不只在CSV里。本章补齐从数据库、API、Excel读写数据的能力，以及生产级Python代码所需的现代化工具链。

### 15.1 从数据库取数：SQLAlchemy + pd.read_sql

```python
# ---- 安装 ----
# pip install sqlalchemy pymysql  # pymysql=MySQL驱动, sqlalchemy=统一接口

from sqlalchemy import create_engine, text
import pandas as pd
import os

# ---- 创建连接引擎 ----
# 连接引擎管理连接池——不用每次查询都重新连接。像一个"常驻的电话线"
# 数据库URL格式: dialect+driver://user:password@host:port/database
engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@localhost:3306/ecommerce"
)

# ---- 基本查询 ----
# read_sql是智能版——传表名自动SELECT *，传SQL字符串执行查询。日常都用read_sql()
df = pd.read_sql("SELECT * FROM orders WHERE year = 2024", engine)

# 聚合查询：结果和df.groupby()效果完全一致
df = pd.read_sql("""
    SELECT city, SUM(amount) AS total_revenue, COUNT(*) AS order_count
    FROM orders
    WHERE year = 2024
    GROUP BY city
    ORDER BY total_revenue DESC
""", engine)

# ---- 参数化查询（防止SQL注入！） ----
# 不要用f-string拼接SQL！用params参数
start_date = '2024-01-01'
end_date = '2024-12-31'
min_amount = 1000

df = pd.read_sql("""
    SELECT * FROM orders
    WHERE date BETWEEN %(start)s AND %(end)s
      AND amount > %(min_amount)s
""", engine, params={
    'start': start_date,
    'end': end_date,
    'min_amount': min_amount
})

# ---- read_sql_table：直接读整张表 ----
df = pd.read_sql_table('products', engine, columns=['id', 'name', 'price'])

# ---- 分块读取大表（chunksize） ----
total = 0
for chunk in pd.read_sql("SELECT * FROM huge_table", engine, chunksize=10000):
    total += chunk['amount'].sum()
print(f"总金额: {total}")

# ---- 写入数据库 ----
df.to_sql('analysis_results', engine,
          if_exists='replace',   # 'fail'|'replace'|'append'
          index=False,
          dtype={'user_id': sqlalchemy.types.BigInteger()})  # 控制列类型

# ---- SQLite（本地轻量数据库，练习/小项目首选） ----
engine_sqlite = create_engine('sqlite:///analysis.db')
df.to_sql('summary', engine_sqlite, if_exists='replace', index=False)

# ---- Context Manager安全关闭（确保异常时也会关闭） ----
from contextlib import closing
with closing(create_engine('sqlite:///test.db')) as tmp_engine:
    result = pd.read_sql("SELECT 1", tmp_engine)
```

### 15.2 调用REST API：requests

```python
import requests
import time
import pandas as pd

# ---- GET请求：获取数据 ----
response = requests.get(
    'https://api.example.com/v1/orders',
    params={'date_from': '2024-01-01', 'date_to': '2024-01-31', 'limit': 100},
    headers={'Authorization': f'Bearer {os.getenv("API_TOKEN")}'},
    timeout=30                     # 30秒超时，防止无限等待
)

# 状态码检查
if response.status_code == 200:
    data = response.json()         # JSON → dict/list
    df = pd.DataFrame(data['items'])
elif response.status_code == 429:
    print("被限流了，等待后重试...")
elif response.status_code >= 500:
    print("服务器内部错误")

# ---- POST请求：提交数据 ----
payload = {'name': '新用户', 'email': 'user@example.com'}
response = requests.post('https://api.example.com/v1/users',
                         json=payload,
                         headers={'Content-Type': 'application/json'})

# ---- 处理分页（自动翻页直到取完） ----
def fetch_all_pages(base_url, params, headers, max_pages=100):
    """自动翻页取完全部数据"""
    all_data = []
    page = 1
    while page <= max_pages:
        params['page'] = page
        response = requests.get(base_url, params=params, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"第{page}页请求失败: {response.status_code}")
            break

        data = response.json()
        items = data.get('items', data.get('data', []))

        if not items:  # 没有更多数据——停止翻页
            break

        all_data.extend(items)
        page += 1

        # 礼貌等待（遵守API限流规则）
        time.sleep(0.2)

    return pd.DataFrame(all_data)

# ---- 限流重试（Exponential Backoff） ----
def request_with_retry(url, max_retries=3, base_delay=1):
    """指数退避——每次等待时间翻倍，避免服务端负载雪崩"""
    for attempt in range(max_retries):
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:  # 限流
            wait = base_delay * (2 ** attempt)
            print(f"被限流，等待{wait}秒后重试...")
            time.sleep(wait)
        else:
            response.raise_for_status()     # 其他错误直接抛异常
    raise Exception(f"重试{max_retries}次后仍失败")
```

### 15.3 格式化Excel：openpyxl

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.chart import BarChart, Reference, LineChart
from openpyxl.utils import get_column_letter

# ---- 写入格式化的Excel报告 ----
wb = Workbook()
ws = wb.active
ws.title = "月度经营分析"

# 标题行（加粗、居中、背景色）
header_font = Font(name='微软雅黑', bold=True, size=12, color='FFFFFF')
header_fill = PatternFill(start_color='2F5496', end_color='2F5496', fill_type='solid')
header_alignment = Alignment(horizontal='center', vertical='center')

headers = ['月份', 'GMV(万元)', '订单量', '客单价(元)', '环比增长(%)']
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = header_alignment

# 写入数据行
data = [
    ['1月', 1200, 35000, 343, None],
    ['2月', 980, 31000, 316, -18.3],
    ['3月', 1350, 38000, 355, 37.8],
]

for row_idx, row_data in enumerate(data, 2):
    for col_idx, value in enumerate(row_data, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.alignment = Alignment(horizontal='center')

        # 增长列为正=绿色，负=红色
        if col_idx == 5 and value is not None:
            if value > 0:
                cell.font = Font(color='008000', bold=True)
            else:
                cell.font = Font(color='FF0000', bold=True)

# 数字格式
for row in range(2, len(data) + 2):
    ws.cell(row=row, column=2).number_format = '#,##0'       # 千分位
    ws.cell(row=row, column=3).number_format = '#,##0'
    ws.cell(row=row, column=4).number_format = '#,##0.00'
    ws.cell(row=row, column=5).number_format = '0.0'

# 添加边框
thin_border = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)
for row in ws.iter_rows(min_row=1, max_row=len(data)+1, max_col=5):
    for cell in row:
        cell.border = thin_border

# 自动调整列宽
for col in range(1, 6):
    ws.column_dimensions[get_column_letter(col)].width = 16

# ---- 在Excel中插入图表 ----
chart = BarChart()
chart.title = "月度GMV趋势"
chart.style = 10
chart.y_axis.title = 'GMV（万元）'
chart.x_axis.title = '月份'

data_ref = Reference(ws, min_col=2, min_row=1, max_row=len(data)+1, max_col=2)
categories_ref = Reference(ws, min_col=1, min_row=2, max_row=len(data)+1)
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(categories_ref)
chart.shape = 4

ws.add_chart(chart, "A8")

# 保存
wb.save('月度经营分析报告.xlsx')
```

### 15.4 现代路径操作：pathlib

```python
from pathlib import Path

# pathlib替代os.path——面向对象的路径操作，可读性远好于os.path的字符串拼接

# ---- 路径创建 ----
data_dir = Path('data/2024/raw')
data_dir.mkdir(parents=True, exist_ok=True)  # 递归创建目录（不怕已存在）

# ---- 路径拼接（"/"运算符） ----
output_file = data_dir / 'sales.csv'         # data/2024/raw/sales.csv
output_file = data_dir / '2024' / '01' / 'report.xlsx'

# ---- 路径属性 ----
print(output_file.name)       # report.xlsx
print(output_file.stem)       # report（无后缀名）
print(output_file.suffix)     # .xlsx
print(output_file.parent)     # data/2024/raw/2024/01
print(output_file.parent.parent)  # data/2024/raw/2024

# ---- 文件操作 ----
# 读取
content = (data_dir / 'readme.txt').read_text(encoding='utf-8')

# 写入
(data_dir / 'output.txt').write_text("分析完成", encoding='utf-8')

# 检查
if (data_dir / 'config.yaml').exists():
    print("配置文件存在")
if (data_dir / 'data.csv').is_file():
    print("是文件不是目录")

# ---- 遍历文件（glob） ----
# 递归查找所有CSV
csv_files = list(data_dir.rglob('*.csv'))

# 只查当前目录层
csv_files = list(data_dir.glob('*.csv'))

# 复杂过滤
for f in data_dir.rglob('*.csv'):
    if f.stat().st_size > 1024:  # 大于1KB
        print(f"处理大文件: {f}")

# ---- 批量重命名 ----
for f in Path('data').rglob('*.csv'):
    new_name = f.with_suffix('.bak')
    f.rename(new_name)

# ---- pathlib vs os.path 对比 ----
# os.path.join('data', '2024', 'raw', 'sales.csv')   # 字符串拼接
# Path('data') / '2024' / 'raw' / 'sales.csv'         # 面向对象，可读性更好
```

### 15.5 日志系统：logging

```python
import logging

# ---- 配置日志（数据分析项目标准配置） ----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('analysis.log', encoding='utf-8'),  # 写入文件
        logging.StreamHandler()                                   # 控制台输出
    ]
)
logger = logging.getLogger('sales_analysis')

# ---- 使用日志（替代print） ----
def clean_and_aggregate(input_path, output_path):
    logger.info(f"开始清洗数据: {input_path}")
    df = pd.read_csv(input_path)

    before = len(df)
    df = df.dropna(subset=['amount', 'date'])
    after = len(df)
    logger.info(f"删除{ before - after}条缺失记录 ({before}→{after})")

    try:
        result = df.groupby('category')['amount'].agg(['sum', 'mean', 'count'])
        result.to_csv(output_path)
        logger.info(f"聚合完成，输出{len(result)}行 → {output_path}")
    except Exception as e:
        logger.exception(f"聚合过程出错: {e}")  # exception自动附带堆栈
        raise

# ---- 日志级别 ----
# DEBUG: 详细调试信息（开发中）
# INFO: 关键步骤记录（生产推荐——知道"跑了什么/跑了多久/结果如何"）
# WARNING: 需要关注但不阻断的异常（如某个文件缺失但可跳过）
# ERROR: 操作失败但程序可继续（如单次API调用失败后重试中）
# CRITICAL: 程序无法继续运行

# ---- 给不同模块创建独立logger ----
data_logger = logging.getLogger('data_pipeline.data')
analysis_logger = logging.getLogger('data_pipeline.analysis')

# 设置不同级别
logging.getLogger('data_pipeline.data').setLevel(logging.DEBUG)
logging.getLogger('matplotlib').setLevel(logging.WARNING)   # 屏蔽matplotlib的DEBUG日志
logging.getLogger('urllib3').setLevel(logging.WARNING)      # 屏蔽HTTP连接日志
```

### 15.6 类型标注：type hints

```python
from typing import Optional, Union, List, Dict, Tuple, Any, Callable, Literal
from typing import TypedDict
import pandas as pd
import numpy as np

# ---- 基础类型标注 ----
def calculate_growth(current: float, previous: float) -> float:
    """计算增长率"""
    if previous == 0:
        return float('inf')
    return (current - previous) / previous

# ---- Optional：可为None ----
def get_column(df: pd.DataFrame, name: str) -> Optional[pd.Series]:
    """安全获取列，不存在返回None"""
    return df[name] if name in df.columns else None

# ---- Union：多种类型 ----
def format_number(value: Union[int, float, str], decimals: int = 2) -> str:
    return f"{float(value):.{decimals}f}"

# ---- List/Dict泛型 ----
def aggregate_metrics(df: pd.DataFrame,
                      group_col: str,
                      metrics: List[str]) -> Dict[str, Dict[str, float]]:
    """返回: {'销售额': {'mean': 123, 'sum': 456}, ...}"""
    return {m: {'mean': df.groupby(group_col)[m].mean(),
                'sum': df.groupby(group_col)[m].sum()
                } for m in metrics}

# ---- Callable：接受函数作为参数 ----
def apply_transformations(df: pd.DataFrame,
                          transformers: List[Callable[[pd.DataFrame], pd.DataFrame]]
                          ) -> pd.DataFrame:
    for transform in transformers:
        df = transform(df)
    return df

# ---- Literal：限定可选值 ----
def create_chart(data: pd.DataFrame,
                 chart_type: Literal['bar', 'line', 'scatter', 'heatmap']
                 ) -> None:
    if chart_type == 'bar':
        pass  # 画柱状图

# ---- DataFrame的类型标注（Pandas 2.0+） ----
# 在函数签名中标注DataFrame的列类型
def analyze_sales(df: pd.DataFrame) -> pd.Series:
    return df.groupby('category')['amount'].sum()

# TypedDict：定义配置字典结构
class AnalysisConfig(TypedDict):
    input_file: str
    date_column: str
    metric_columns: List[str]
    group_by: str
    min_sample_size: int
    output_format: Literal['csv', 'excel', 'parquet']

def run_analysis(config: AnalysisConfig) -> pd.DataFrame:
    df = pd.read_csv(config['input_file'])
    return df.groupby(config['group_by'])[config['metric_columns']].mean()

# ---- 类型检查工具 ----
# mypy script.py          # 静态类型检查（不运行代码）
# pip install mypy
```

### 15.7 测试：pytest + 数据断言

```python
# ---- 安装 ----
# pip install pytest

# ====== 文件: test_analysis.py ======

import pytest
import pandas as pd
import numpy as np
from pandas.testing import assert_frame_equal, assert_series_equal

# 要在测试前准备好测试fixture
@pytest.fixture
def sample_sales_df():
    """测试用的DataFrame fixture"""
    return pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100, freq='D'),
        'product': np.random.choice(['A', 'B', 'C', 'D'], 100),
        'quantity': np.random.poisson(5, 100),
        'price': np.random.lognormal(3, 0.5, 100),
        'amount': np.random.normal(500, 100, 100)
    })

# ====== 数据质量测试 ======

def test_no_missing_values_in_key_column(sample_sales_df):
    """关键列不存在缺失值"""
    assert sample_sales_df['date'].isna().sum() == 0, "日期列存在缺失值"
    assert sample_sales_df['product'].isna().sum() == 0, "产品列存在缺失值"

def test_quantity_is_positive(sample_sales_df):
    """数量必须为正数"""
    assert (sample_sales_df['quantity'] > 0).all(), "存在非正数的数量"

def test_price_in_range(sample_sales_df):
    """价格在合理范围内"""
    assert (sample_sales_df['price'] > 0).all(), "存在负价格"
    assert (sample_sales_df['price'] < 100000).all(), "存在异常高价"

def test_no_duplicate_dates(sample_sales_df):
    """日期不重复"""
    assert sample_sales_df['date'].is_unique, "日期列存在重复"

# ====== 计算逻辑测试 ======

def test_growth_calculation():
    """测试增长率计算"""
    from analysis import calculate_growth
    assert calculate_growth(120, 100) == 0.2
    assert calculate_growth(80, 100) == -0.2
    assert calculate_growth(100, 0) == float('inf')

def test_groupby_aggregation(sample_sales_df):
    """分组聚合结果行数正确"""
    result = sample_sales_df.groupby('product')['amount'].mean()
    assert len(result) == sample_sales_df['product'].nunique()

# ====== 边界条件测试 ======

def test_empty_dataframe():
    """空DataFrame的处理"""
    empty_df = pd.DataFrame(columns=['date', 'product', 'quantity'])
    assert len(empty_df) == 0
    # 聚合空df不报错并以合理方式返回
    result = empty_df.groupby('product')['quantity'].sum()
    assert len(result) == 0

def test_single_row():
    """只有一行数据的处理"""
    single = pd.DataFrame({'product': ['A'], 'amount': [100]})
    assert single.groupby('product')['amount'].mean().iloc[0] == 100

# ====== 回归测试 ======

def test_aggregation_consistent_with_known_result(sample_sales_df):
    """已知结果验证：确保重构不破坏逻辑"""
    result = sample_sales_df.groupby('product')['amount'].agg(['mean', 'sum'])
    # 每个产品的总和应该大于0
    assert (result['sum'] > 0).all()

# ====== 参数化测试 ======

@pytest.mark.parametrize("col,expected_type", [
    ('date', 'datetime64[ns]'),
    ('product', 'object'),
    ('quantity', 'int'),
])
def test_column_dtypes(sample_sales_df, col, expected_type):
    """各列的数据类型正确"""
    assert expected_type in str(sample_sales_df[col].dtype)

# 运行测试: pytest test_analysis.py -v
# 带覆盖率: pytest --cov=. --cov-report=html
```

**数据测试的五大断言模式**：
1. **存在性断言**：列存在、非空、值在允许集合内
2. **范围断言**：数值在业务合理范围内（金额≥0、年龄≤120）
3. **分布断言**：关键分位数不变（回归测试）
4. **行数断言**：操作后行数符合预期（join不膨胀、filter不丢失）
5. **一致性断言**：同一个指标从不同路径计算应得相同结果

---

## 第16章 指标体系与异动归因方法论

### 16.1 指标体系设计

指标体系是将业务目标翻译为可量化、可追踪、可拆解的数据框架。

**核心框架——NSM / OSM / CMOP**：

| 框架 | 全称 | 核心问题 | 产出 |
|------|------|---------|------|
| **NSM** | North Star Metric | "公司成功的唯一关键指标是什么？" | 一个北极星指标 |
| **OSM** | Objective → Strategy → Measure | "每个策略的成败如何衡量？" | 策略-指标映射表 |
| **CMOP** | Customer Journey → Metric → Owner → Process | "每个环节谁负责？对什么指标负责？" | 全链路指标责任矩阵 |

```python
# ---- 指标体系设计的Python实践 ----
import pandas as pd
import numpy as np

# 以电商为例定义指标体系
# NSM（北极星指标）= GMV（已支付）
# 拆解公式：
# GMV = 流量(浏览UV) × 浏览→加购率 × 加购→下单率 × 下单→支付率 × 客单价

metrics_tree = {
    'level_1': {
        '北极星指标': 'GMV(已支付)',
        'owner': 'VP of Product',
        'formula': 'UV × 浏览→加购率 × 加购→下单率 × 下单→支付率 × 笔单价'
    },
    'level_2': {
        '流量(浏览UV)': {
            'owner': '增长负责人',
            'sub_metrics': ['DAU', '新用户占比', '渠道来源分布', '落地页CTR']
        },
        '浏览→加购转化率': {
            'owner': '商品运营',
            'sub_metrics': ['商品详情页转化率', '价格竞争力指数', '库存健康度', '评分分布']
        },
        '加购→下单转化率': {
            'owner': '交易体验',
            'sub_metrics': ['客单价', '凑单率', '优惠券使用率', '配送时效展示']
        },
        '下单→支付转化率': {
            'owner': '支付团队',
            'sub_metrics': ['支付成功率', '支付方式可用率', '风控拦截率']
        }
    },
    'level_3': {
        'health_metrics': ['用户留存率', 'NPS', '退货率', '客服投诉量'],
        'counter_metrics': ['优惠券总成本', '获客成本', '物流成本占GMV比例']
    }
}

# 设计原则：
# 1. 北极星指标必须反映用户获得的核心价值（不是收入！而是使用量）
# 2. 每个指标都有owner（问责到人）
# 3. 必须配counter-metrics（防止"刷GMV不顾利润"）
# 4. 指标拆解树每层MECE（互斥且穷尽）
```

### 16.2 异动归因——当指标异常时怎么做

当周报显示"GMV跌了15%"，数据分析师的价值不只在"发现了跌"，而在"知道为什么跌"和"谁该负责"。

**七层深挖法——从现象到根因的完整排查路径**：

```
第0层：确认是不是"假跌"
├── 数据管道正常吗？→ 埋点/ETL有没有延迟或断
├── 去年同期也跌吗？→ 季节性因素
├── 口径一致吗？→ 上个月改了定义但没人通知
└── 结论：是真的跌了，还是"看着像跌"

第1层：拆解——哪个因子变化最大？
GMV = UV × 转化率 × 客单价
├── 拆解三个因子的环比变化
├── 每个因子贡献了多少（乘法分解→对数转换→比例分摊）
└── 结论：GMV跌15%→80%来自UV跌12%，15%来自转化率跌2%，5%来自客单价变化

第2层：定位——哪个业务环节？
└── 流量跌了→哪个渠道？/转化率跌了→哪一步（浏览→加购？加购→下单？支付？）

第3层：分割——哪个人群/品类/城市？
├── 新用户 vs 老用户？→ 主要是新用户跌（渠道质量变化?）
├── 哪个品类？→ 服饰跌30%，食品涨5%
└── 哪个城市？→ 一线城市跌20%，三四线持平

第4层：归因——外部原因 or 内部变更？
├── 外部：竞品活动？行业舆情？季节/天气？节假日偏移？
├── 内部：产品改版？算法调整？运营活动到期？定价变更？
└── 逐日回溯：找到"断崖点"→对比当天发生的事件

第5层：量化——外部vs内部各占多少？
├── 用DID/因果推断量化单个因子的贡献
├── 排除法：逐步控制变量看剩余效应
└── 结论：降价促销的贡献=+5pp，竞品活动的侵蚀=-12pp，自然波动=-8pp

第6层：建议——下一步怎么办？
├── 短期止血：恢复关键策略（重新上线活动/回滚算法/修bug）
├── 中期观察：设监控阈值，如果3天回到正常=一次性事件
└── 长期优化：改产品/改策略/改监控
```

```python
# ---- 异动归因的Python实现 ----
def decompose_gmv_change(df_current, df_baseline):
    """GMV变化率拆解为UV/转化率/客单价的贡献"""
    # 当前周期
    uv_c = df_current['uv'].sum()
    cvr_c = df_current['orders'].sum() / uv_c   # 转化率
    asp_c = df_current['gmv'].sum() / df_current['orders'].sum()  # 客单价
    gmv_c = df_current['gmv'].sum()

    # 基线周期
    uv_b = df_baseline['uv'].sum()
    cvr_b = df_baseline['orders'].sum() / uv_b
    asp_b = df_baseline['gmv'].sum() / df_baseline['orders'].sum()
    gmv_b = df_baseline['gmv'].sum()

    # 对数分解（精确分配各因子贡献）
    log_ratio = np.log(gmv_c / gmv_b)
    uv_contrib = np.log(uv_c / uv_b) / log_ratio * 100
    cvr_contrib = np.log(cvr_c / cvr_b) / log_ratio * 100
    asp_contrib = np.log(asp_c / asp_b) / log_ratio * 100

    total_change = (gmv_c / gmv_b - 1) * 100

    return pd.DataFrame({
        '因子': ['UV(流量)', '转化率', '客单价', '合计'],
        '贡献比例(%)': [round(uv_contrib, 1), round(cvr_contrib, 1),
                       round(asp_contrib, 1), round(uv_contrib+cvr_contrib+asp_contrib, 1)],
        '当前值': [f"{uv_c:,}", f"{cvr_c:.2%}", f"¥{asp_c:.2f}", f"¥{gmv_c:,.0f}"],
        '基线值': [f"{uv_b:,}", f"{cvr_b:.2%}", f"¥{asp_b:.2f}", f"¥{gmv_b:,.0f}"]
    })

# ---- 按维度切片诊断 ----
def slice_diagnosis(df_current, df_baseline, slice_col, metric_col):
    """按某个维度切片，找变化最大的切片"""
    curr = df_current.groupby(slice_col)[metric_col].sum()
    base = df_baseline.groupby(slice_col)[metric_col].sum()

    change_pct = (curr - base) / base * 100
    contribution = (curr - base) / (curr.sum() - base.sum()) * 100

    result = pd.DataFrame({
        '当前': curr,
        '基线': base,
        '变化(%)': change_pct.round(1),
        '贡献(%)': contribution.round(1)
    }).sort_values('贡献(%)', ascending=False)

    return result

# 使用示例
# channel_diag = slice_diagnosis(df_this_week, df_last_week, 'channel', 'gmv')
# city_diag = slice_diagnosis(df_this_week, df_last_week, 'city', 'gmv')
# product_diag = slice_diagnosis(df_this_week, df_last_week, 'category', 'gmv')
```

### 16.3 经营分析报告结构

一份VP看得懂的经营分析报告的标准结构：

```
1. 结论先行（Executive Summary，3-5句话）
   └── 格式: 本期[指标]达到[数值]，环比[+X%]，高于/低于目标[Ypp]。
            主要驱动因素是[A]和[B]，分别贡献[X1%]和[X2%]。
            需要关注的负面信号是[C]。
            建议下一步[具体行动]。

2. 关键指标看板（1页Dashboard）
   └── 核心指标+子指标的趋势图（带目标线和置信区间）

3. 异动归因（2-3页深度分析）
   └── 第N层拆解+切片+归因结论

4. 风险与机会（1页前瞻）
   └── 未来1-2个月可能影响指标的已知因素

5. 附录（数据来源/口径/假设/限制）
```

**三条灵魂问题（写报告前必须能答上）**：
1. "所以呢？（So What?）"——这个数据变化对业务意味着什么？
2. "然后呢？（Now What?）"——应该做什么？谁来做？什么时候做？
3. "你怎么知道？（How Do You Know?）"——能用什么方式验证这个结论？

---

## 第17章 用户增长分析体系

### 17.1 AARRR海盗模型

AARRR是用户增长分析的经典框架，覆盖用户从获客到传播的完整生命周期：

```
Acquisition  →  Activation  →  Retention  →  Revenue  →  Referral
   (获客)         (激活)         (留存)        (变现)       (传播)

指标：
  获客成本CAC    新用户激活率   次日/7日/30日  ARPU/LTV    邀请率/K-factor
  渠道ROI       首次关键行为   留存率        转化率        病毒系数
```

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# ---- 构建AARRR指标体系 ----
aarrr_metrics = {
    'Acquisition(获客)': {
        '核心指标': ['CAC(获客成本)', '各渠道新用户数', 'CPA(每激活成本)'],
        '诊断指标': ['渠道质量分', '自然量占比', 'CPM/CPC趋势']
    },
    'Activation(激活)': {
        '核心指标': ['新用户激活率', '激活时长(分钟)', '首次关键行为完成率'],
        '诊断指标': ['注册漏斗各步转化率', '新手引导完成率', '首次内容消费率']
    },
    'Retention(留存)': {
        '核心指标': ['次日留存率', '7日留存率', '30日留存率', 'DAU/MAU'],
        '诊断指标': ['不同获客渠道的留存率', '不同用户分群的留存衰减曲线']
    },
    'Revenue(变现)': {
        '核心指标': ['ARPU', 'ARPPU(付费用户ARPU)', 'LTV', '付费率'],
        '诊断指标': ['首充金额分布', '复购率', '退款率', '优惠券ROI']
    },
    'Referral(传播)': {
        '核心指标': ['邀请率', 'K-factor(病毒系数)', '分享率'],
        '诊断指标': ['邀请转化漏斗', '被邀请人留存vs自然用户对比']
    }
}
```

### 17.2 Cohort留存分析

留存分析是用户增长中最核心的分析方法——回答"不同时期进来的用户，谁留下来了、留了多久"。

```python
# ---- Cohort分析：周期留存热力图 ----
def build_cohort_matrix(df, period='M'):
    """
    构建Cohort留存矩阵
    df需包含: user_id, first_purchase_date(首次购买时间), purchase_date
    返回: cohort × period 的留存率矩阵
    """
    # 1. 确定每个用户的Cohort（首次购买月份）
    df['cohort'] = df['first_purchase_date'].dt.to_period(period)
    df['period'] = df['purchase_date'].dt.to_period(period)

    # 2. 计算用户从Cohort到每个Period的月数间距
    df['period_number'] = (df['period'] - df['cohort']).apply(lambda x: x.n)

    # 3. 构建Cohort × Period的留存矩阵
    cohort_matrix = df.groupby(['cohort', 'period_number'])['user_id'].nunique().unstack()

    # 4. 转为留存率（每个Cohort第0期=100%）
    cohort_sizes = cohort_matrix[0]
    retention = cohort_matrix.divide(cohort_sizes, axis=0)

    return retention

# ---- 可视化留存热力图 ----
def plot_cohort_heatmap(retention):
    """Cohort留存热力图"""
    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(retention * 100,
                annot=True, fmt='.1f', cmap='YlOrRd',
                vmin=0, vmax=100,
                linewidths=0.5, linecolor='white',
                cbar_kws={'label': '留存率(%)'},
                ax=ax)
    ax.set_title('Cohort留存矩阵', fontsize=16, fontweight='bold')
    ax.set_xlabel('第N期', fontsize=12)
    ax.set_ylabel('用户Cohort', fontsize=12)

# ---- 不同渠道的留存曲线对比 ----
def plot_retention_curves_by_channel(df):
    """按获客渠道画留存衰减曲线"""
    fig, ax = plt.subplots(figsize=(10, 6))

    for channel in df['acquisition_channel'].unique():
        channel_users = df[df['acquisition_channel'] == channel]
        cohort_retention = build_cohort_matrix(channel_users, period='W')
        avg_retention = cohort_retention.mean()  # 所有cohort的均值留存曲线
        ax.plot(avg_retention.index, avg_retention.values * 100,
                'o-', label=channel, linewidth=2, markersize=5)

    ax.set_xlabel('周数', fontsize=12)
    ax.set_ylabel('平均留存率(%)', fontsize=12)
    ax.set_title('各渠道用户留存衰减曲线对比', fontsize=14, fontweight='bold')
    ax.legend(title='获客渠道')
    ax.grid(True, linestyle='--', alpha=0.4)
```

### 17.3 LTV（用户生命周期价值）计算

```python
# ---- 方法1：简单LTV（基于历史数据） ----
def simple_ltv(df, period_days=365):
    """
    简单LTV = ARPU × 平均生命周期
    生命周期 = 1 / (1 - 留存率)
    """
    # 计算日ARPU
    daily_revenue = df['revenue'].sum() / (df['date'].max() - df['date'].min()).days
    daily_active_users = df['user_id'].nunique()
    arpu_per_day = daily_revenue / daily_active_users if daily_active_users > 0 else 0

    # 计算平均生命周期（天）
    retention_rate = df.groupby('user_id')['date'].nunique().mean() / period_days
    if retention_rate < 1:
        avg_lifetime_days = 1 / (1 - retention_rate)
    else:
        avg_lifetime_days = period_days  # 100%留存=无限生命周期→用观察期上限

    ltv = arpu_per_day * avg_lifetime_days
    return ltv, arpu_per_day, avg_lifetime_days

# ---- 方法2：基于Cohort的预测LTV ----
def cohort_based_ltv(retention_matrix, revenue_per_user_per_period):
    """
    基于留存曲线预测LTV
    LTV = Σ(revenue_per_period × retention_t)  for t=0..∞
    """
    avg_retention_curve = retention_matrix.mean()

    # 拟合指数衰减模型: retention_t = a * e^(-b*t)
    from scipy.optimize import curve_fit

    def exp_decay(t, a, b):
        return a * np.exp(-b * t)

    periods = avg_retention_curve.index.values
    values = avg_retention_curve.values

    # 只拟合非零部分
    valid = values > 0
    if sum(valid) < 3:
        return revenue_per_user_per_period * sum(values)

    popt, _ = curve_fit(exp_decay, periods[valid], values[valid],
                        p0=[values[0], 0.1], maxfev=5000)

    # 预测未来36期
    future_periods = np.arange(36)
    predicted_retention = exp_decay(future_periods, *popt)
    predicted_retention = np.clip(predicted_retention, 0, 1)

    ltv = revenue_per_user_per_period * predicted_retention.sum()
    return ltv

# ---- LTV/CAC 比率——判断增长是否健康 ----
def ltv_cac_health(ltv, cac):
    """LTV/CAC健康度判断"""
    ratio = ltv / cac
    if ratio >= 3:
        status = "✅ 健康（可加速增长）"
    elif ratio >= 1:
        status = "⚠️ 边缘（需优化获客效率或提升LTV）"
    else:
        status = "🔴 危险（每获一个用户都在亏钱）"
    return ratio, status
```

### 17.4 漏斗分析

```python
# ---- 构建转化漏斗 ----
def build_funnel(df, steps):
    """
    构建漏斗数据
    steps: [{'name': '曝光', 'condition': df['event']=='impression'},
            {'name': '点击', 'condition': df['event']=='click'}, ...]
    """
    funnel_data = []
    for step in steps:
        count = step['condition'].sum()
        funnel_data.append({'步骤': step['name'], '用户数': count})

    funnel_df = pd.DataFrame(funnel_data)
    funnel_df['整体转化率'] = funnel_df['用户数'] / funnel_df['用户数'].iloc[0]
    funnel_df['步骤间转化率'] = funnel_df['用户数'] / funnel_df['用户数'].shift(1)
    return funnel_df

# ---- 漏斗可视化 ----
def plot_funnel(funnel_df):
    """绘制转化漏斗图"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 左图：漏斗柱状图
    steps = funnel_df['步骤'].values
    counts = funnel_df['用户数'].values
    colors = sns.color_palette('viridis', len(steps))

    axes[0].barh(steps, counts, color=colors, edgecolor='white', height=0.6)

    # 标注每步转化率
    for i, (step, count) in enumerate(zip(steps, counts)):
        rate = funnel_df['步骤间转化率'].iloc[i] if i > 0 else 1.0
        label = f"{count:,} ({rate:.1%})" if i > 0 else f"{count:,}"
        axes[0].text(count + max(counts) * 0.02, i, label,
                     va='center', fontsize=10)

    axes[0].set_xlabel('用户数', fontsize=12)
    axes[0].set_title('转化漏斗', fontsize=14, fontweight='bold')
    axes[0].invert_yaxis()

    # 右图：步骤间转化率（识别最需要优化的环节）
    step_rates = funnel_df['步骤间转化率'].iloc[1:].values
    step_labels = [f"{steps[i]}→{steps[i+1]}" for i in range(len(steps)-1)]
    bar_colors = ['#e74c3c' if r < 0.3 else '#f39c12' if r < 0.6 else '#2ecc71'
                  for r in step_rates]

    bars = axes[1].bar(step_labels, step_rates, color=bar_colors, edgecolor='white')
    for bar, rate in zip(bars, step_rates):
        axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                     f'{rate:.1%}', ha='center', fontsize=10, fontweight='bold')
    axes[1].set_ylabel('步骤间转化率', fontsize=12)
    axes[1].set_title('步骤间转化率（红色=瓶颈）', fontsize=14, fontweight='bold')
    axes[1].set_ylim(0, 1)
    axes[1].grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
```

### 17.5 渠道ROI分析

```python
# ---- 渠道四维评估模型 ----
def channel_four_dimension_analysis(df):
    """
    渠道四维评估：
    1. 量（用户量）——够不够大
    2. 质（留存/活跃）——用户好不好
    3. 价（CAC/LTV）——划不划算
    4. 增（增长潜力）——还能不能扩大
    """
    analysis = df.groupby('channel').agg(
        新用户数=('user_id', 'nunique'),
        CAC=('cost', 'sum'),            # 总成本/用户数
        次日留存率=('day1_retained', 'mean'),
        30日LTV=('ltv_30d', 'mean'),
        付费率=('is_paying', 'mean')
    ).reset_index()

    analysis['CAC'] = analysis['CAC'] / analysis['新用户数']
    analysis['LTV/CAC'] = analysis['30日LTV'] / analysis['CAC']

    # 四象限分类
    analysis['渠道类别'] = np.where(
        (analysis['LTV/CAC'] >= 2) & (analysis['次日留存率'] >= analysis['次日留存率'].median()),
        '⭐ 优质渠道（加大投入）',
        np.where((analysis['LTV/CAC'] >= 2) & (analysis['次日留存率'] < analysis['次日留存率'].median()),
                 '⚠️ 高转化低留存（优化承接）',
                 np.where((analysis['LTV/CAC'] < 2) & (analysis['次日留存率'] >= analysis['次日留存率'].median()),
                          '🔧 高留存高成本（优化获客效率）',
                          '🛑 低质高价（削减或放弃）'))
    )

    return analysis.sort_values('新用户数', ascending=False)
```

---

## 第18章 业务行业深度手册

### 18.1 电商（阿里/拼多多/京东/抖音电商）

**核心公式**：
```
GMV = DAU × 浏览转化率 × 下单转化率 × 支付转化率 × 笔单价 × 人均购买频次

核心利润 = GMV × 抽成率
           - 补贴/优惠券成本
           - 退款/退货成本
           - 获客成本(新客CAC × 新客数)
           - 物流成本
```

**关键分析场景**：

| 场景 | 排查路径 | 典型结论 |
|------|---------|---------|
| GMV跌了 | UV跌→哪个渠道？/转化率跌→哪一步？/客单价跌→哪个品类？ | 80%来自UV跌(搜索渠道掉量) |
| 大促ROI | 活动期GMV增量÷活动总成本 → 扣除自然增长 → 长期留存衰减 | 首日ROI虚高30%(未扣自然增长) |
| 品类结构 | 各品类GMV占比 vs 利润占比 → 流量分配是否合理 | 服饰贡献50%GMV但只占30%流量位 |
| 会员价值 | 会员vs非会员的客单价/复购率/LTV → 会员ROI | 付费会员LTV是非会员的4.2倍 |

### 18.2 内容/信息流（抖音/快手/小红书/B站/番茄小说）

**核心公式**：
```
DAU = 昨日留存DAU + 新用户DAU + 回流DAU

用户时长 = DAU × 人均时长
         = DAU × (Feed浏览时长 + 搜索时长 + 直播观看时长)

内容消费深度 = 人均内容消费条数 × 单条消费完成率

创作者飞轮：
  创作者数 × 人均发布 → 内容池大小 → 推荐分发 → 用户消费时长
  → 互动(赞/评/转) → 创作者激励 → 更多创作者
```

**关键分析场景**：

| 场景 | 排查路径 | 典型结论 |
|------|---------|---------|
| 时长跌了 | 按内容类型拆解→哪个类型时长跌了？→该类型的内容供给跌了还是CTR跌了？ | 短视频时长跌12%→原因是搞笑品类头部创作者停更3天 |
| 留存跌了 | Cohort分析→哪个Cohort的留存拐了？→该Cohort的新用户首日体验变了？ | W37起用户7日留存跌→那周上线了新推荐策略 |
| 创作者流失 | 按粉丝量分层→大V/中V/小V的流失率 → 大V流失=平台危机 | 10万+粉创作者月流失率3%→需加强变现工具 |

### 18.3 出行（滴滴/高德/美团打车）

**核心公式**：
```
完单率 = 完单量 / 发单量

供需健康度：
  应答率 = 被接单量 / 发单量  （需求端）
  司机利用率 = 有单司机数 / 在线司机数 （供给端）

四象限诊断：
  高应答率×高利用率 = 供需平衡 ✅
  高应答率×低利用率 = 司机过剩 → 减少司机补贴
  低应答率×高利用率 = 供不应求 → 提高价格/调度/司机激励
  低应答率×低利用率 = 匹配效率差 → 优化派单算法

GMV = 完单量 × 客单价
    = DAU × 发单率 × 应答率 × 完单率 × 平均行程金额
```

### 18.4 游戏（腾讯/网易/miHoYo）

**核心公式**：
```
日流水 = DAU × 付费率 × ARPPU(付费用户平均收入)
       = 新增用户 × 首日付费率 + 存量付费用户 × 持续付费率

LTV = Σ(第t天留存率 × 第t天ARPU)，t=0→∞

关键节奏：
  首日LTV → 决定买量回本周期
  7日LTV → 决定短期ROI
  30日LTV → 决定长期是否赚钱
  90日LTV → 能赚多少
```

**玩家分层（金字塔模型）**：
| 层级 | 占比 | 付费特征 | 运营策略 |
|------|------|---------|---------|
| 鲸鱼(大R) | <1% | ARPPU极高，单人可以养活服务器 | 专属客服、定制化服务 |
| 海豚(中R) | 5-10% | 持续付费、月卡/战令 | 内容持续更新、限定皮肤 |
| 小鱼(小R) | 15-25% | 首充/月卡/偶尔充值 | 首充奖励优化、限时优惠 |
| 免费玩家 | 65-80% | 零付费但贡献活跃 | 广告变现、社交传播 |

### 18.5 外卖/即时配送（美团/饿了么）

**核心公式**：
```
GMV = DAU × 下单率 × 客单价
完单率 = 商户接单率 × 骑手取餐率 × 配送完成率

平台价值 = 商户侧价值 + 用户侧价值 + 骑手侧价值
商户侧 = 曝光 × 进店率 × 下单率 × 客单价 - 佣金率 × GMV
```

**30分钟送达的完整漏斗**：
```
用户下单 → 商家接单(30s) → 骑手接单(60s) → 骑手到店(300s)
→ 取餐完成(120s) → 送达(900s)
目标：总时长 < 1800s(30min)
瓶颈识别：每个环节记录P50/P90/P99时长 → 优化最长的环节
```

### 18.6 社交（微信/QQ/陌陌/Soul）

**核心公式**：
```
DAU = 消息发送DAU + 内容消费DAU(朋友圈/动态/直播) + 工具DAU

社交网络健康度：
  人均好友数 × 日互动率 = 网络密度
  网络密度越大 → 用户越难离开（迁移成本越高）
```

### 18.7 金融科技（蚂蚁/微众/京东金融）

**核心公式**：
```
收入 = 生息资产规模 × 净息差 + 手续费收入 - 信用成本(坏账)

信贷核心链路：
  授信通过率 × 支用率 × 在贷余额 × 利率 - 逾期率 × 损失率

风控关键指标：
  - 通过率（越高越好，但不能以牺牲风险为代价）
  - vintages逾期率（按放款月份追踪逾期表现）
  - 额度使用率（给了额度用户用了吗？用了多少？）
```

---

### 18.8 行业分析速查表

| 行业 | 北极星指标 | 核心拆解公式 | 最多被问的面试题 |
|------|-----------|-------------|----------------|
| 电商 | GMV(已支付) | GMV = UV×CVR×ASP×Freq | "DAU涨了但GMV跌了，可能是什么原因？" |
| 内容 | 用户总时长 | 时长 = DAU×人均时长 | "人均时长涨了但留存跌了，你怎么看？" |
| 出行 | 完单率 | 完单率 = 完单量÷发单量 | "应答率从85%跌到78%，怎么判断是供还是需的问题？" |
| 游戏 | DAU×付费率×ARPPU | LTV = Σ(留存_t × ARPU_t) | "一款新游戏首周数据不错但30日留存崩了，分析什么？" |
| 外卖 | 完单量 | 交易额 = 用户×频次×客单价 | "恶劣天气完单率为什么反而跌了？（供需双杀）" |
| 社交 | DAU | DAU = 留存DAU+新增+回流 | "DAU稳定但消息量降了30%，你分析什么？" |
| 金融 | 在贷余额×净息差 | 利润 = 利息收入-资金成本-坏账 | "通过率从20%提到25%，但逾期率没变，是好事吗？" |

---

> **最终更新说明**：本文档共18章，覆盖Python数据分析从基础语法（第1章）、数据处理栈（第2-5章）、统计分析（第6章）、机器学习（第7章）、实战案例（第8章）、高性能计算（第9章）、时间序列（第10章）、因果推断（第11章）、数据质量（第12章）、MLOps（第13章）、可组合数据栈（第14章）、数据工程基础（第15章）、指标体系（第16章）、用户增长（第17章）到行业业务深度（第18章）的完整知识体系。总计400+可运行代码示例，60+分析场景，覆盖数据分析师从入行到资深所需的全部硬技能与业务思维。

> *文档持续更新中 · 最后修订：2026年5月*
```
