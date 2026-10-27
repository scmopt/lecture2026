"""SCM.275x - 発展サプライチェーンシステム計画とネットワーク設計

輸送問題 (Transportation Problem)

ノートブック「01Transportation Problem_ja.ipynb」のコードセルを抽出して
単一のPythonスクリプトにまとめたもの。各セル直前の説明は、対応する関数・クラスの
DocStringに記載している。

必要なパッケージ（必要に応じてインストール）::

    pip install amplpy     # AMPLのPythonインターフェース
    python -m amplpy.modules install highs   # HiGHSソルバー
    pip install pandas    # データ分析・操作用ライブラリ Pandas
    pip install folium     # インタラクティブマップ作成用ライブラリ Folium
    pip install geopy      # 距離計算・地理データ処理用ライブラリ Geopy
"""

# 必要なパッケージをすべてインポート

import pandas as pd                   # データの操作と分析用
from amplpy import AMPL, modules      # 数理モデルを解くためのAMPL（amplpy）
import folium                         # インタラクティブマップ作成用
import folium.plugins as plugins      # folium用追加プラグイン
from geopy.distance import geodesic   # 2地点間の測地線距離計算用


# ===========================================================================
# ヘルパー関数 (Helper functions)
# ===========================================================================

def plot_nodes(map,                         # ノードをプロットするFoliumマップオブジェクト
               nodes,                       # ノードオブジェクトの辞書（各ノードは緯度や経度などの属性を含む）
               icon,                        # 地図上のマーカーに使用するアイコン記号
               color,                       # マーカーアイコンの色
               background_color,            # マーカーアイコンの背景色
               ):
    """地図上へのノードのプロット

    foliumを使って地図上にノードをプロットする関数。
    """

    # 辞書内の各ノードをループ処理
    for node in nodes.values():

        # foliumマーカーを作成
        marker = folium.Marker(
            location=[node.lat, node.lon],              # マーカーの位置を設定
            popup = (node.ID + "-" + node.name),        # ノードIDと名前のポップアップを作成
            icon=plugins.BeautifyIcon(                  # マーカーアイコンを作成
                icon=icon,
                icon_shape="circle",
                text_color=color,                       # マーカーの色を設定
                border_color=color,
                background_color=background_color,
            )
        )

        # foliumマーカーを地図に追加
        marker.add_to(map)


def compute_geodesic_distance(origin,       # 出発地ノードオブジェクト
                              destination,  # 目的地ノードオブジェクト
                              unit='km'):   # 単位（'km' または 'mi'）、デフォルトは 'km'
    """測地線距離の計算

    2地点間の測地線距離を計算する関数。
    """

    # 出発地と目的地から座標（緯度と経度）を抽出
    origin_coordinates = [origin.lat, origin.lon]
    destination_coordinates = [destination.lat, destination.lon]

    # 指定された単位（'km' または 'mi'）に基づいて距離を計算
    if unit == 'km':
        distance = geodesic(origin_coordinates, destination_coordinates).km  # キロメートル単位で距離を計算
    elif unit == 'mi':
        distance = geodesic(origin_coordinates, destination_coordinates).mi  # マイル単位で距離を計算

    return distance  # 計算された距離を返す


def plot_flows(map,                   # フローをプロットするFoliumマップオブジェクト
               vars,                  # 最適解のフロー量の辞書（キーはノードペア）
               nodes,                 # ノードオブジェクトの辞書
               max_width = 30,        # フロー線の最大幅（デフォルトは30）
               color = 'grey',        # フローを表す線の色（デフォルトは灰色）
               opacity = 0.5):        # 線の不透明度（デフォルトは0.5）
    """地図上へのフローのプロット

    foliumを使って地図上にフローをプロットする関数。
    """

    # 線の太さを正規化するためにフローの最大値を検索
    max_val = max(vars.values())

    # フロー決定変数をループ処理（キーはノードペアを表す）
    for (node1_key, node2_key), var in vars.items():

        # 正のフローのみプロット
        if var > 0:

            # 線を描画するためのノード座標を取得
            points = [[nodes[node1_key].lat, nodes[node1_key].lon],
                      [nodes[node2_key].lat, nodes[node2_key].lon]]


            # ノード間のフローを表すPolyLineを地図に追加
            folium.PolyLine(points,
                            color=color,                                # 線の色を設定
                            weight=var / max_val * max_width,         # フロー値に基づいて線の太さを正規化
                            opacity=opacity,                            # 線の不透明度を設定
                            popup=var).add_to(map)                    # 地図のポップアップにフロー値を表示


# ===========================================================================
# データ設定と前処理 - ノード (Nodes)
# ===========================================================================

def load_customers():
    """入力ファイルの読み込み（顧客）

    顧客データを含むファイルをpandas DataFrameに読み込む。
    """
    # 顧客データを含むファイル
    customer_data_file = 'https://raw.githubusercontent.com/scm275/problem_sets_scm275/main/transportation_problem/customers.csv'

    # 顧客データをpandas DataFrameに読み込み
    customers_df = pd.read_csv(customer_data_file)

    # データの確認のため先頭数行を表示
    print(customers_df.head())
    return customers_df


def load_suppliers():
    """入力ファイルの読み込み（サプライヤー）

    サプライヤー（供給業者）データを含むファイルをpandas DataFrameに読み込む。
    """
    # サプライヤー（供給業者）データを含むファイル
    supplier_data_file = 'https://raw.githubusercontent.com/scm275/problem_sets_scm275/main/transportation_problem/suppliers.csv'

    # サプライヤーデータをpandas DataFrameに読み込み
    suppliers_df = pd.read_csv(supplier_data_file)

    # データの確認のため先頭数行を表示
    print(suppliers_df.head())
    return suppliers_df


class Customer():
    """クラスの定義

    顧客（Customer）オブジェクトを表すクラス。
    """
    def __init__(self, ID, name, lat, lon, demand):
        self.ID = ID              # 顧客ID
        self.name = name          # 顧客名
        self.lat = lat            # 顧客の緯度
        self.lon = lon            # 顧客の経度
        self.demand = demand      # 顧客の需要量


class Supplier():
    """サプライヤー（Supplier）オブジェクトを表すクラス。"""
    def __init__(self, ID, name, lat, lon, supply):
        self.ID = ID            # サプライヤーID
        self.name = name        # サプライヤー名
        self.lat = lat          # サプライヤーの緯度
        self.lon = lon          # サプライヤーの経度
        self.supply = supply    # サプライヤーの供給可能量


def create_nodes(customers_df, suppliers_df):
    """ノードオブジェクトの作成

    顧客・サプライヤーオブジェクトの辞書を作成し、nodes辞書に統合する。
    """
    # ノードオブジェクトを格納する空の辞書を初期化
    nodes = dict()

    # 顧客オブジェクトの辞書を作成
    customers = dict()
    for i, row in customers_df.iterrows():
        customers[row['ID']] = Customer(ID=row['ID'],           # 顧客ID
                                        name=row['name'],       # 顧客名
                                        lat=row['lat'],         # 顧客の緯度
                                        lon=row['lon'],         # 顧客の経度
                                        demand=row['demand'])   # 顧客の需要量

    # 顧客辞書を既存のnodes辞書に統合
    nodes = {**nodes, **customers}

    # サプライヤーオブジェクトの辞書を作成
    suppliers = dict()
    for i, row in suppliers_df.iterrows():
        suppliers[row['ID']] = Supplier(ID=row['ID'],           # サプライヤーID
                                        name=row['name'],       # サプライヤー名
                                        lat=row['lat'],         # サプライヤーの緯度
                                        lon=row['lon'],         # サプライヤーの経度
                                        supply=row['supply'])   # サプライヤーの供給可能量

    # サプライヤー辞書を既存のnodes辞書に統合
    nodes = {**customers, **suppliers}

    return nodes, customers, suppliers


def check_supply_demand(customers, suppliers):
    """総供給量が総需要量以上（または以下）であることを確認する。"""

    # すべてのサプライヤーからの総供給量を格納する変数を初期化
    total_supply = 0
    # すべてのサプライヤーオブジェクトをループ処理し、供給量を合計
    for x in suppliers.values():
        total_supply += x.supply

    # すべての顧客からの総需要量を格納する変数を初期化
    total_demand = 0
    # すべての顧客オブジェクトをループ処理し、需要量を合計
    for x in customers.values():
        total_demand += x.demand

    # 計算された総供給量を出力
    print('Total Supply:', total_supply)

    # 計算された総需要量を出力
    print('Total Demand:', total_demand)


def visualize_nodes(customers, suppliers):
    """ノードオブジェクトの可視化

    米国を中心としたズームレベル5の新しい地図を作成し、顧客とサプライヤーをプロットする。
    (OpenStreetMapのiframe制限やCartoDBのAPIキー要求を回避するため、Esriのライトグレー背景地図を使用)
    """
    map = folium.Map(
        location=[40, -95.0],
        zoom_start=5,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        attr='Esri'
    )
    # 顧客の位置を店舗アイコン、緑色、黄色背景でプロット
    plot_nodes(map=map, nodes=customers, icon='store', color='green', background_color='yellow')

    # サプライヤーの位置を工場アイコン、オレンジ色、黄色背景でプロット
    plot_nodes(map=map, nodes=suppliers, icon='industry', color='orange', background_color='yellow')

    # 地図の視覚化を向上させるためのタイルレイヤーを追加 (cartodbpositronテーマ)
    #folium.TileLayer('cartodbpositron').add_to(map)

    # プロットされたすべてのデータを地図に表示
    return map


# ===========================================================================
# データ設定と前処理 - アーク (Arcs)
# ===========================================================================

def compute_distances(customers, suppliers):
    """アークの距離

    顧客とサプライヤー間の距離を格納する辞書を作成する。
    """
    distances = dict()
    for s, supplier in suppliers.items():                                                                   # サプライヤーをループ処理
        for c, customer in customers.items():                                                               # 顧客をループ処理
            distances[s, c] = compute_geodesic_distance(origin=customer, destination=supplier, unit='km')   # キロメートル単位で距離を計算して格納
    return distances


def compute_unit_costs(customers, suppliers, distances):
    """アークのコスト

    顧客とサプライヤー間の単位コストを格納する辞書を作成する。
    """
    cost_unit_km = 1.2  # 1kmあたりの単位輸送コスト

    # 顧客とサプライヤー間の単位コストを格納する辞書を作成
    unit_cost = dict()
    for s, supplier in suppliers.items():                                                           # サプライヤーをループ処理
        for c, customer in customers.items():                                                       # 顧客をループ処理
            unit_cost[s, c] = distances[s, c] * cost_unit_km                                        # 距離にkmあたりコストを掛けて単位コストを計算
    return unit_cost


# ===========================================================================
# 最適化モデル
# ===========================================================================

# 輸送問題のAMPLモデル
TRANSPORTATION_MODEL = r"""
set SUPPLIERS;                                  # サプライヤーの集合
set CUSTOMERS;                                  # 顧客の集合

param supply {SUPPLIERS} >= 0;                  # サプライヤーの供給可能量
param demand {CUSTOMERS} >= 0;                  # 顧客の需要量
param unit_cost {SUPPLIERS, CUSTOMERS} >= 0;    # 単位輸送コスト

# サプライヤーと顧客間のフローを表す決定変数
var flow {SUPPLIERS, CUSTOMERS} >= 0;

# 目的関数：総輸送コストの最小化
minimize TotalCost:
    sum {s in SUPPLIERS, c in CUSTOMERS} unit_cost[s, c] * flow[s, c];

# 需要制約
subject to Demand {c in CUSTOMERS}:
    sum {s in SUPPLIERS} flow[s, c] = demand[c];

# 供給制約
subject to Supply {s in SUPPLIERS}:
    sum {c in CUSTOMERS} flow[s, c] <= supply[s];
"""


def solve_transportation(customers, suppliers, unit_cost, solver="highs"):
    """最適化モデルの作成と求解

    AMPLで輸送問題のモデルを作成し、データをamplpyで渡して求解する。
    最適なフロー量の辞書 {(サプライヤーID, 顧客ID): フロー量} を返す。
    """
    # amplpyでインストールしたソルバーモジュールを読み込み
    modules.load()

    # 新しいAMPLモデルを作成
    ampl = AMPL()
    ampl.eval(TRANSPORTATION_MODEL)

    # 集合とパラメータのデータを設定
    ampl.set["SUPPLIERS"] = list(suppliers.keys())
    ampl.set["CUSTOMERS"] = list(customers.keys())
    ampl.param["supply"] = {s: supplier.supply for s, supplier in suppliers.items()}
    ampl.param["demand"] = {c: customer.demand for c, customer in customers.items()}
    ampl.param["unit_cost"] = unit_cost

    # モデルの求解
    ampl.option["solver"] = solver
    ampl.solve()
    print("Solve result:", ampl.solve_result)
    print("Total Cost:", ampl.obj["TotalCost"].value())

    # 最適解のフロー量を取得
    flows = ampl.var["flow"].get_values().to_dict()
    return flows


# ===========================================================================
# 解の可視化と分析
# ===========================================================================

def visualize_solution(customers, suppliers, nodes, flow_vars):
    """解の可視化と分析

    地図上での顧客とサプライヤーの位置、およびその間のフローを可視化する。
    """
    # 米国を中心としたズームレベル5の新しい地図を作成
    map = folium.Map([40, -95.0], zoom_start=5)

    # 顧客の位置を店舗アイコン、緑色、黄色背景でプロット
    plot_nodes(map=map, nodes=customers, icon='store', background_color='yellow', color='green')

    # サプライヤーの位置を工場アイコン、オレンジ色、黄色背景でプロット
    plot_nodes(map=map, nodes=suppliers, icon='industry', background_color='yellow', color='orange')

    # サプライヤーと顧客間のフローを最大線幅20でプロット
    plot_flows(map=map, max_width=20, vars=flow_vars, nodes=nodes)

    # 地図の視覚化を向上させるためのタイルレイヤーを追加 (cartodbpositronテーマ)
    #folium.TileLayer('cartodbpositron').add_to(map)

    # プロットされたすべてのデータを地図に表示
    return map


if __name__ == "__main__":
    customers_df = load_customers()
    suppliers_df = load_suppliers()
    nodes, customers, suppliers = create_nodes(customers_df, suppliers_df)
    check_supply_demand(customers, suppliers)

    # ノートブックでは地図をセル出力として表示するが、スクリプトではHTMLに保存する
    visualize_nodes(customers, suppliers).save("transportation_nodes.html")

    distances = compute_distances(customers, suppliers)
    unit_cost = compute_unit_costs(customers, suppliers, distances)

    flow_vars = solve_transportation(customers, suppliers, unit_cost)

    visualize_solution(customers, suppliers, nodes, flow_vars).save("transportation_flows.html")
