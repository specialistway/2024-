import pandas as pd
from gurobipy import Model, GRB, quicksum
# 加载附件1和附件2中的数据

file4='updated_crop_data_with_profit_new.xlsx'
# 读取文件中的所有表格

planting_data_2023 = pd.read_excel(file4, sheet_name='Sheet1')


# 提取所需信息
planting_data_2023_processed = planting_data_2023[['种植地块', '作物编号', '植物名称', '种植面积/亩', '季节','利润']]
planting_data_2023_processed.columns = ['Land Name', 'Crop ID', 'Crop Name', 'Area', 'Planting Season','Profit']



s=pd.DataFrame({
    'Land Name': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12', 'B13', 'B14', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6'],
    'Crop Name': ['小麦', '玉米', '玉米', '黄豆', '绿豆', '谷子', '小麦', '黑豆', '红豆', '绿豆', '爬豆', '谷子', '小麦', '谷子', '高粱', '黍子', '黄豆', '玉米', '莜麦', '大麦', '荞麦', '南瓜', '黄豆', '红薯', '小麦', '红豆'],
    'Season': ['单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季', '单季'],
    'Planted Area': [80, 55, 35, 72, 68, 55, 60, 46, 40, 28, 25, 86, 55, 44, 50, 25, 60, 45, 35, 20, 15, 13, 15, 18, 27, 20]
}
)
# 获取地块和作物信息
lands = planting_data_2023_processed['Land Name'].unique()
crops = planting_data_2023_processed['Crop Name'].unique()
seasons = ['第一季', '第二季']  # 假设每年有两个种植季节
# 加载初始数据（例如2023年的数据）
#planting_data_2023 = pd.read_excel('path_to_your_data_file.xlsx', sheet_name='2023年种植情况')

# 定义时间跨度
years = list(range(2024, 2031))  # 2024年到2030年

# 初始化结果存储
all_solutions = {}

all_solutions[2023]=s
# 滚动优化过程
for year in years:
    print(f"Optimizing for the year: {year}")

    # 初始化模型
    model = Model(f"Crop_Optimization_{year}")

    # 定义决策变量
    x = model.addVars(lands, crops, seasons, vtype=GRB.CONTINUOUS, name=f"x_{year}")


    # 添加约束条件
    # 每块地在每个季节至少要种植一个作物

    for land in lands:
        for season in seasons:



            # 获取前两年的数据
            if year > 2024:
                last_year_data = all_solutions[year - 1]
                last_last_year_data = all_solutions[year - 2]
            elif year == 2024:
                last_year_data = planting_data_2023_processed
                last_last_year_data = planting_data_2023_processed

            # 确保不重茬种植
            for crop in last_year_data[last_year_data['Land Name'] == land]['Crop Name']:
                model.addConstr(x[land, crop, season] == 0, name=f"no_repeat_planting_{year}_{land}_{crop}_{season}")

            # 确保三年内至少种植一次豆类作物
            if season == '单季':  # 仅在第一季约束，以便三年内至少种植一次
                legume_planted_last_two_years = (
                        (last_year_data[last_year_data['Land Name'] == land]['Crop Name'].str.contains(
                            '豆').sum() > 0) +
                        (last_last_year_data[last_last_year_data['Land Name'] == land]['Crop Name'].str.contains(
                            '豆').sum() > 0)
                )

                # 如果前两年没有种植豆类作物，确保本年种植
                if legume_planted_last_two_years == 0:
                    model.addConstr(
                        quicksum(x[land, crop, season] for crop in crops if '豆' in crop) >= 1,
                        name=f"legume_rotation_{year}_{land}"
                    )

            # 添加土地面积限制的约束条件
            model.addConstr(
                quicksum(x[land, crop, season] for crop in crops) <=
                planting_data_2023_processed[planting_data_2023_processed['Land Name'] == land]['Area'].iloc[0],
                name=f"area_limit_{year}_{land}_{season}"
            )

    # 计算 Profit 时的修改
    crop_data = planting_data_2023_processed[
        (planting_data_2023_processed['Land Name'] == land) &
        (planting_data_2023_processed['Crop Name'] == crop)
        ]

    if not crop_data.empty:
        profit_value = crop_data['Profit'].iloc[0]
    else:
        profit_value = 0  # 或者处理缺少数据的逻辑

    # 使用 profit_value
    profit = quicksum(
        x[land, crop, season] * profit_value
        for land in lands for crop in crops for season in seasons
    )

    model.setObjective(profit, GRB.MAXIMIZE)

    # 优化模型
    model.optimize()

    # 保存当前年份的解决方案
    solution = pd.DataFrame({
        'Land Name': [land for land in lands for crop in crops for season in seasons],
        'Crop Name': [crop for land in lands for crop in crops for season in seasons],
        'Season': [season for land in lands for crop in crops for season in seasons],
        'Planted Area': [x[land, crop, season].x for land in lands for crop in crops for season in seasons]
    })

    all_solutions[year] = solution
    #print(solution)
    # 将解决方案保存为Excel文件
    solution.to_excel(f"crop_optimization_solution_{year}.xlsx", index=False)

    print(f"Year {year} optimization completed and saved.")
