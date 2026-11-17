"""SCM.275x - 発展サプライチェーンシステム計画とネットワーク設計

積換問題 - Python 演習 (Transshipment Problem - Python Exercise)

ノートブック「02Transshipment_Problem_Python_Exercise.ipynb」のコードセルを抽出して
単一のPythonスクリプトにまとめたもの。各セル直前の説明は、対応する関数・クラスの
DocStringに日本語で記載している。

必要なパッケージ（必要に応じてインストール）::

    pip install amplpy                       # AMPL の Python インターフェース
    python -m amplpy.modules install highs   # HiGHS ソルバー
    pip install pandas                       # データ分析・操作用ライブラリ Pandas
    pip install folium                       # インタラクティブマップ作成用ライブラリ Folium
    pip install geopy                        # 距離計算・地理データ処理用ライブラリ Geopy
"""

# 必要なパッケージをすべてインポート

import pandas as pd                   # データの操作と分析用
from amplpy import AMPL, modules      # 数理モデルを解くための AMPL（amplpy）
import folium                         # インタラクティブマップ作成用
import folium.plugins as plugins      # folium 用追加プラグイン
from geopy.distance import geodesic   # 2地点間の測地線距離計算用


# ===========================================================================
# ヘルパー関数 (Helper functions)
# ===========================================================================

def plot_nodes(map,                         # ノードをプロットする Folium マップオブジェクト
               nodes,                       # ノードオブジェクトの辞書（各ノードは緯度や経度などの属性を含む）
               icon,                        # 地図上のマーカーに使用するアイコン記号
               color,                       # マーカーアイコンの色
               background_color,            # マーカーアイコンの背景色
               ):
    """地図上へのノードのプロット

    folium を使って地図上にノードをプロットする関数。
    """
    # 辞書内の各ノードをループ処理
    for node in nodes.values():

        # folium マーカーを作成
        marker = folium.Marker(
            location=[node.lat, node.lon],              # マーカーの位置を設定
            popup=(node.ID + "-" + node.name),          # ノードIDと名前のポップアップを作成
            icon=plugins.BeautifyIcon(                  # マーカーアイコンを作成
                icon=icon,
                icon_shape="circle",
                text_color=color,
                border_color=color,
                background_color=background_color,
            )
        )

        # folium マーカーを地図に追加
        marker.add_to(map)


def compute_geodesic_distance(origin,       # 出発地ノードオブジェクト
                              destination,  # 目的地ノードオブジェクト
                              unit='km'):   # 単位（'km' または 'mi'）
    """測地線距離の計算

    2地点間の測地線距離を計算する関数。
    """
    # 出発地と目的地から座標（緯度と経度）を抽出
    origin_coordinates = [origin.lat, origin.lon]
    destination_coordinates = [destination.lat, destination.lon]

    # 指定された単位に基づいて距離を計算
    if unit == 'km':
        distance = geodesic(origin_coordinates, destination_coordinates).km  # キロメートル単位で計算
    elif unit == 'mi':
        distance = geodesic(origin_coordinates, destination_coordinates).mi  # マイル単位で計算

    return distance  # 計算された距離を返す


def plot_flows(map,                   # フローをプロットする Folium マップオブジェクト
               vars,                  # 最適解のフロー量の辞書（キーはノードペア）
               nodes,                 # ノードオブジェクトの辞書
               max_width=30,          # フローの最大線幅（デフォルトは 30）
               color='grey',          # フローを表す線の色（デフォルトは 'grey'）
               opacity=0.5):          # 線の不透明度（デフォルトは 0.5）
    """地図上へのフローのプロット

    folium を使って地図上にフローをプロットする関数。
    """
    # 線幅を正規化するために最大フロー値を取得
    max_val = max(vars.values())

    # フロー決定変数（キーはノードペア）を反復処理
    for (node1_key, node2_key), var in vars.items():

        # 正のフローのみプロット
        if var > 0:

            # 線をプロットするためのノード座標を取得
            points = [[nodes[node1_key].lat, nodes[node1_key].lon],
                      [nodes[node2_key].lat, nodes[node2_key].lon]]

            # ノード間のフローを表す PolyLine を地図に追加
            folium.PolyLine(points,
                            color=color,                                # 線の色を設定
                            weight=var / max_val * max_width,           # フロー値に基づいて線幅を正規化
                            opacity=opacity,                            # 線の不透明度を設定
                            popup=var).add_to(map)                      # ポップアップにフロー値を表示


# ===========================================================================
# データの設定と前処理 (Data setup and preprocessing)
# ===========================================================================
# ノード (Nodes) - クラスの定義 (Definition of Classes)

class Customer():
    """顧客クラス

    データ設定と前処理におけるノード定義として、顧客（Customer）オブジェクトを表すクラス。
    """

    def __init__(self, ID, name, lat, lon, demand):
        self.ID = ID              # 顧客のID
        self.name = name          # 顧客名
        self.lat = lat            # 顧客の緯度
        self.lon = lon            # 顧客の経度
        self.demand = demand      # 顧客の需要量


class Supplier():
    """サプライヤークラス

    データ設定と前処理におけるノード定義として、サプライヤー（Supplier）オブジェクトを表すクラス。
    """

    def __init__(self, ID, name, lat, lon, supply):
        self.ID = ID            # サプライヤーのID
        self.name = name        # サプライヤー名
        self.lat = lat          # サプライヤーの緯度
        self.lon = lon          # サプライヤーの経度
        self.supply = supply    # サプライヤーの供給可能量


class Warehouse():
    """倉庫クラス

    データ設定と前処理におけるノード定義として、倉庫（Warehouse）オブジェクトを表すクラス。
    """

    def __init__(self, ID, name, lat, lon, capacity):
        self.ID = ID              # 倉庫のID
        self.name = name          # 倉庫名
        self.lat = lat            # 倉庫の緯度
        self.lon = lon            # 倉庫の経度
        self.capacity = capacity  # 倉庫の容量


# 入力ファイルの読み込み (Reading input files)

def load_customers():
    """顧客データの読み込み

    顧客データファイルを読み込み、pandas DataFrame を返す。
    """
    customer_data_file = 'https://raw.githubusercontent.com/scm275/problem_sets_scm275/main/transshipment_problem/customers.csv'
    customers_df = pd.read_csv(customer_data_file)
    print(customers_df.head())
    return customers_df


def load_suppliers():
    """サプライヤーデータの読み込み

    サプライヤーデータファイルを読み込み、pandas DataFrame を返す。
    """
    supplier_data_file = 'https://raw.githubusercontent.com/scm275/problem_sets_scm275/main/transshipment_problem/suppliers.csv'
    suppliers_df = pd.read_csv(supplier_data_file)
    print(suppliers_df.head())
    return suppliers_df


def load_warehouses():
    """倉庫データの読み込み

    倉庫データファイルを読み込み、pandas DataFrame を返す。
    """
    warehouse_data_file = 'https://raw.githubusercontent.com/scm275/problem_sets_scm275/main/transshipment_problem/warehouses.csv'
    warehouses_df = pd.read_csv(warehouse_data_file)
    print(warehouses_df.head())
    return warehouses_df


def create_nodes(customers_df, suppliers_df, warehouses_df):
    """ノードオブジェクトの作成

    顧客・サプライヤー・倉庫の DataFrame から各オブジェクトの辞書と統合辞書 nodes を作成する。
    """
    nodes = dict()

    # 顧客オブジェクトの辞書を作成
    customers = dict()
    for i, row in customers_df.iterrows():
        customers[row['ID']] = Customer(ID=row['ID'],
                                        name=row['name'],
                                        lat=row['lat'],
                                        lon=row['lon'],
                                        demand=row['demand'])
    nodes = {**nodes, **customers}

    # サプライヤーオブジェクトの辞書を作成
    suppliers = dict()
    for i, row in suppliers_df.iterrows():
        suppliers[row['ID']] = Supplier(ID=row['ID'],
                                        name=row['name'],
                                        lat=row['lat'],
                                        lon=row['lon'],
                                        supply=row['supply'])
    nodes = {**nodes, **suppliers}

    # 倉庫オブジェクトの辞書を作成
    warehouses = dict()
    for i, row in warehouses_df.iterrows():
        warehouses[row['ID']] = Warehouse(ID=row['ID'],
                                          name=row['name'],
                                          lat=row['lat'],
                                          lon=row['lon'],
                                          capacity=row['capacity'])
    nodes = {**nodes, **warehouses}

    return nodes, customers, suppliers, warehouses


def visualize_nodes(customers, suppliers, warehouses):
    """ノードオブジェクトの可視化

    ヨーロッパを中心とした地図上に、顧客・倉庫・サプライヤーの各ノードをプロットして返す。
    """
    # ヨーロッパを中心としたズームレベル5の新しい地図を作成
    map = folium.Map([50, 10.0], zoom_start=5)

    # 顧客の位置を店舗アイコン、緑色、黄色背景でプロット
    plot_nodes(map=map, nodes=customers, icon='store', color='green', background_color='yellow')

    # 倉庫の位置を倉庫アイコン、青色、黄色背景でプロット
    plot_nodes(map=map, nodes=warehouses, icon='warehouse', color='blue', background_color='yellow')

    # サプライヤーの位置を工場アイコン、オレンジ色、黄色背景でプロット
    plot_nodes(map=map, nodes=suppliers, icon='industry', color='orange', background_color='yellow')

    # 地図の視覚化を向上させるためのタイルレイヤーを追加（cartodbpositron テーマ）
    folium.TileLayer('cartodbpositron').add_to(map)

    return map


# ===========================================================================
# アーク (Arcs)
# ===========================================================================

def compute_distances(suppliers, warehouses, customers):
    """アーク間の距離の計算

    サプライヤーと倉庫間、および倉庫と顧客間の測地線距離（km）の辞書を作成する。
    """
    distances = dict()
    for s, supplier in suppliers.items():
        for w, warehouse in warehouses.items():
            distances[s, w] = compute_geodesic_distance(origin=supplier, destination=warehouse, unit='km')

    for w, warehouse in warehouses.items():
        for c, customer in customers.items():
            distances[w, c] = compute_geodesic_distance(origin=warehouse, destination=customer, unit='km')

    return distances


def compute_unit_costs(suppliers, warehouses, customers, distances,
                       cost_unit_km_supplier_warehouse=15,
                       cost_unit_km_warehouse_customer=20):
    """アークコストの計算

    サプライヤー・倉庫間および倉庫・顧客間の単位輸送コストの辞書を作成する。
    """
    unit_cost = dict()

    for s, supplier in suppliers.items():
        for w, warehouse in warehouses.items():
            unit_cost[s, w] = distances[s, w] * cost_unit_km_supplier_warehouse

    for w, warehouse in warehouses.items():
        for c, customer in customers.items():
            unit_cost[w, c] = distances[w, c] * cost_unit_km_warehouse_customer

    return unit_cost


# ===========================================================================
# 最適化モデル (Optimization model)
# ===========================================================================

# 積換問題の AMPL モデル
TRANSSHIPMENT_MODEL = r"""
set SUPPLIERS;                                              # サプライヤーの集合
set WAREHOUSES;                                             # 倉庫の集合
set CUSTOMERS;                                              # 顧客の集合

param supply {SUPPLIERS} >= 0;                              # サプライヤーの供給可能量
param demand {CUSTOMERS} >= 0;                              # 顧客の需要量
param unit_cost_sw {SUPPLIERS, WAREHOUSES} >= 0;            # サプライヤー・倉庫間の単位輸送コスト
param unit_cost_wc {WAREHOUSES, CUSTOMERS} >= 0;            # 倉庫・顧客間の単位輸送コスト

# サプライヤー・倉庫間および倉庫・顧客間のフローを表す決定変数
var flow_sw {SUPPLIERS, WAREHOUSES} >= 0;
var flow_wc {WAREHOUSES, CUSTOMERS} >= 0;

# 目的関数：総輸送コストの最小化
minimize TotalCost:
    sum {s in SUPPLIERS, w in WAREHOUSES} unit_cost_sw[s, w] * flow_sw[s, w]
    + sum {w in WAREHOUSES, c in CUSTOMERS} unit_cost_wc[w, c] * flow_wc[w, c];

# 需要制約
subject to Demand {c in CUSTOMERS}:
    sum {w in WAREHOUSES} flow_wc[w, c] = demand[c];

# 供給制約
subject to Supply {s in SUPPLIERS}:
    sum {w in WAREHOUSES} flow_sw[s, w] <= supply[s];

# フロー保存制約（倉庫への流入量と流出量が等しい）
subject to FlowBalance {w in WAREHOUSES}:
    sum {s in SUPPLIERS} flow_sw[s, w] = sum {c in CUSTOMERS} flow_wc[w, c];
"""


def solve_transshipment(suppliers, warehouses, customers, unit_cost, solver="highs"):
    """最適化モデルの作成と求解

    AMPL で積換問題（Transshipment Problem）のモデルを作成し、
    データを amplpy で渡して求解する。
    最適なフロー量の辞書 {(出発ノードID, 到着ノードID): フロー量} を返す。

    課題1（Task 1）:
        倉庫の容量制約（capacity constraints）を考慮するように、
        以下の最適化モデルを修正すること。
    """
    # amplpy でインストールしたソルバーモジュールを読み込み
    modules.load()

    # 新しい AMPL モデルを作成
    ampl = AMPL()
    ampl.eval(TRANSSHIPMENT_MODEL)

    # 集合とパラメータのデータを設定
    ampl.set["SUPPLIERS"] = list(suppliers.keys())
    ampl.set["WAREHOUSES"] = list(warehouses.keys())
    ampl.set["CUSTOMERS"] = list(customers.keys())
    ampl.param["supply"] = {s: supplier.supply for s, supplier in suppliers.items()}
    ampl.param["demand"] = {c: customer.demand for c, customer in customers.items()}
    ampl.param["unit_cost_sw"] = {(s, w): unit_cost[s, w] for s in suppliers for w in warehouses}
    ampl.param["unit_cost_wc"] = {(w, c): unit_cost[w, c] for w in warehouses for c in customers}

    # モデルの求解
    ampl.option["solver"] = solver
    ampl.solve()
    print("Solve result:", ampl.solve_result)
    print("Total Cost:", ampl.obj["TotalCost"].value())

    # 最適解のフロー量を取得
    flow_sw = ampl.var["flow_sw"].get_values().to_dict()
    flow_wc = ampl.var["flow_wc"].get_values().to_dict()
    return {**flow_sw, **flow_wc}


# ===========================================================================
# 解の可視化と分析 (Solution visualization and analysis)
# ===========================================================================

def visualize_solution(customers, suppliers, warehouses, nodes, flow_vars):
    """解の可視化と分析

    地図上での顧客・倉庫・サプライヤーの位置、および最適なフローを可視化する。
    """
    # ヨーロッパを中心としたズームレベル5の新しい地図を作成
    map = folium.Map([50, 10.0], zoom_start=5)

    # 顧客の位置を店舗アイコン、緑色、黄色背景でプロット
    plot_nodes(map=map, nodes=customers, icon='store', color='green', background_color='yellow')

    # 倉庫の位置を倉庫アイコン、青色、黄色背景でプロット
    plot_nodes(map=map, nodes=warehouses, icon='warehouse', color='blue', background_color='yellow')

    # サプライヤーの位置を工場アイコン、オレンジ色、黄色背景でプロット
    plot_nodes(map=map, nodes=suppliers, icon='industry', color='orange', background_color='yellow')

    # サプライヤー・倉庫・顧客間のフローを最大線幅20でプロット
    plot_flows(map=map, max_width=20, vars=flow_vars, nodes=nodes)

    # 地図の視覚化を向上させるためのタイルレイヤーを追加（cartodbpositron テーマ）
    folium.TileLayer('cartodbpositron').add_to(map)

    return map


if __name__ == "__main__":
    customers_df = load_customers()
    suppliers_df = load_suppliers()
    warehouses_df = load_warehouses()
    nodes, customers, suppliers, warehouses = create_nodes(
        customers_df, suppliers_df, warehouses_df
    )

    # ノートブックでは地図をセル出力として表示するが、スクリプトでは HTML に保存する
    visualize_nodes(customers, suppliers, warehouses).save("transshipment_nodes.html")

    distances = compute_distances(suppliers, warehouses, customers)
    unit_cost = compute_unit_costs(suppliers, warehouses, customers, distances)

    flow_vars = solve_transshipment(suppliers, warehouses, customers, unit_cost)

    visualize_solution(customers, suppliers, warehouses, nodes, flow_vars).save(
        "transshipment_flows.html"
    )
