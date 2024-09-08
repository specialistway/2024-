import gurobipy as gp
from gurobipy import GRB

# 初始化模型
model = gp.Model("Crop_Plan")

# 输入数据
num_fields = 26  # 地块数量
num_seasons = 1  # 每年两个种植季节
num_years = 7  # 规划期 2024-2030年
crops = ['粮食', '水稻', '蔬菜', '豆类']  # 作物种类
field_types = ['平旱地', '梯田', '山坡地', '水浇地']  # 地块类型

# 假设地块面积数据（假设每块地都是同一类型，数据需要根据实际情况输入）
field_areas = [20, 15, 30, 25, 40, 35, 10, 5, 60, 50, 45, 70, 25, 35, 55, 65, 85, 45, 25, 40, 35, 50, 65, 75, 30, 20,
               25, 35, 45, 55, 60, 70, 80, 90]

# 每种作物的亩产量、成本、销售价格和预期销售量（数据需要根据实际输入）
yield_per_acre = {'粮食': 100, '水稻': 150, '蔬菜': 200, '豆类': 80}
cost_per_acre = {'粮食': 50, '水稻': 70, '蔬菜': 100, '豆类': 40}
price_per_unit = {'粮食': 5, '水稻': 4, '蔬菜': 6, '豆类': 5}
sales_quota = {'粮食': 3000, '水稻': 5000, '蔬菜': 7000, '豆类': 2000}

# 决策变量 x[i,j,k]：第i块地在第j季种植第k种作物的面积
x = model.addVars(num_fields, num_seasons, num_years, crops, lb=0, name="x")

# 滞销量变量 w[k]：第k种作物滞销的量
w = model.addVars(crops, lb=0, name="w")

# 轮作约束的辅助变量 z[i,y]：表示地块 i 在年份 y 是否种植了豆类（0或1）
z = model.addVars(num_fields, num_years, vtype=GRB.BINARY, name="z")

# 目标函数：最大化总收益，减少浪费
model.setObjective(
    gp.quicksum(
        x[i, j, y, k] * yield_per_acre[k] * price_per_unit[k] for i in range(num_fields) for j in range(num_seasons) for
        y in range(num_years) for k in crops)
    - gp.quicksum(x[i, j, y, k] * cost_per_acre[k] for i in range(num_fields) for j in range(num_seasons) for y in
                  range(num_years) for k in crops)
    - 0.001*gp.quicksum(w[k] * yield_per_acre[k] * price_per_unit[k] for k in crops), GRB.MAXIMIZE)

# 约束条件

# 1. 地块面积约束
for i in range(num_fields):
    for y in range(num_years):
        for j in range(num_seasons):
            model.addConstr(gp.quicksum(x[i, j, y, k] for k in crops) <= field_areas[i],
                            name=f"area_constraint_{i}_{j}_{y}")

# 2. 轮作约束：每个地块在三年内至少种一次豆类作物
for i in range(num_fields):
    for y in range(num_years - 2):  # 确保三年窗口检查
        model.addConstr(gp.quicksum(z[i, y_t] for y_t in range(y, y + 3)) >= 1, name=f"rotation_constraint_{i}_{y}")

# 3. 辅助变量约束：z[i,y]等于1当且仅当该年地块i种植了豆类作物
for i in range(num_fields):
    for y in range(num_years):
        model.addConstr(z[i, y] <= gp.quicksum(x[i, j, y, '豆类'] for j in range(num_seasons)),
                        name=f"rotation_tracking_{i}_{y}")

# 4. 滞销约束
for k in crops:
    for y in range(num_years):
        model.addConstr(
            gp.quicksum(x[i, j, y, k] * yield_per_acre[k] for i in range(num_fields) for j in range(num_seasons)) -
            sales_quota[k] <= w[k], name=f"sales_constraint_{k}_{y}")

# 优化模型
model.optimize()

# 输出结果
if model.status == GRB.OPTIMAL:
    total_revenue = 0
    total_cost = 0
    print("\n最优种植方案：")
    for i in range(num_fields):
        for y in range(num_years):
            for j in range(num_seasons):
                for k in crops:
                    if x[i, j, y, k].x > 0:
                        area = x[i, j,y, k].x
                        revenue = area * yield_per_acre[k] * price_per_unit[k]
                        cost = area * cost_per_acre[k]
                        total_revenue += revenue
                        total_cost += cost
                        print(f"地块 {i + 1}，年份 {y + 1}，季节 {j + 1}，种植作物 {k} 的面积为 {x[i, j, y, k].x:.2f} 亩")

    print("\n轮作情况：")
    for i in range(num_fields):
        for y in range(num_years):
            if z[i, y].x > 0:
                print(f"地块 {i + 1} 在年份 {y + 1} 种植了豆类作物")

    # 计算总利润
    total_profit = total_revenue - total_cost
    print(f"总利润为：{total_profit:.2f} 元")

