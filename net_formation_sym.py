import itertools
import numbers
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import networkx as nx

import plotly.graph_objects as go


def plotly_network(graph_stat, pos=None, color_mode=None):

    if color_mode not in ["pair_supported", "net_supported"]:
        color_mode = "pair_supported"

    graph = graph_stat["graph"]
    if not pos:
        pos = nx.spring_layout(graph)

    def create_edge(edge):
        node1, node2 = edge

        return go.Scatter(
            x=[pos[node1][0], pos[node2][0]],
            y=[pos[node1][1], pos[node2][1]],
            line=dict(
                width=1,
                color="#00ff00"
                if graph_stat["exist_edges"][edge][color_mode]
                else "#ff0000",
            ),
            hoverinfo="none",
            mode="lines",
        )

    edge_traces = [create_edge(edge) for edge in graph_stat["exist_edges"]]

    node_x = []
    node_y = []
    node_color = []
    node_text = []
    for node in graph_stat["current_util"]:  # graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_color.append(graph_stat["current_util"][node])
        node_text.append(node)

    node_trace = go.Scatter(
        name="",
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textfont=dict(family="sans serif", size=12, color="Red"),
        # hoverinfo='text',
        customdata=node_color,
        hovertemplate="utility:%{customdata:.2f}",
        marker=dict(
            showscale=True,
            # colorscale options
            #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
            #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
            #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
            colorscale="Blues",
            reversescale=True,
            color=node_color,
            size=20,
            colorbar=dict(
                thickness=15,
                title="Node utility",
                xanchor="left",
                titleside="right",
            ),
            line_width=2,
        ),
    )

    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    return fig


def calc_util(graph, delta, cost):
    util = {x: 0 for x in graph}
    for src, dst in itertools.combinations(graph.nodes, 2):
        paths = nx.shortest_simple_paths(graph, src, dst)
        try:
            u = delta ** (len(next(paths)) - 1)
            util[src] += u
            util[dst] += u
        except nx.NetworkXNoPath:
            pass

    if isinstance(cost, numbers.Number):
        for node, edges in graph.adjacency():
            util[node] -= cost * len(edges)

    return util


def analyze_network(graph, delta, cost):
    current_util = calc_util(graph, delta, cost)

    def new_edge_stat(edge):
        new_graph = nx.from_edgelist(list(graph.edges) + [edge])
        new_graph.add_nodes_from(graph.nodes)
        nodes_util = calc_util(new_graph, delta, cost)
        total_util = sum(nodes_util.values())
        nodes_diff = {
            node: nodes_util[node] - current_util[node] for node in nodes_util
        }
        total_diff = total_util - sum(current_util.values())
        pair_supported = (nodes_diff[edge[0]] >= 0) and (nodes_diff[edge[1]] >= 0)
        net_supported = total_diff >= 0  # and (total_util >= 0)

        return {
            "graph": new_graph,
            "nodes_util": nodes_util,
            "nodes_diff": nodes_diff,
            "total_util": total_util,
            "total_diff": total_diff,
            "pair_supported": pair_supported,
            "net_supported": net_supported,
        }

    def exist_edge_stat(edge):
        new_graph = nx.from_edgelist([x for x in graph.edges if x != edge])
        new_graph.add_nodes_from(graph.nodes)
        nodes_util = calc_util(new_graph, delta, cost)
        total_util = sum(nodes_util.values())
        nodes_diff = {
            node: current_util[node] - nodes_util[node] for node in nodes_util
        }
        total_diff = sum(current_util.values()) - total_util
        pair_supported = (nodes_diff[edge[0]] >= 0) and (nodes_diff[edge[1]] >= 0)
        net_supported = total_diff >= 0  # and (sum(current_util.values()) >= 0)

        return {
            "graph": new_graph,
            "test_list": [x for x in graph.edges if x != edge],
            "nodes_util": nodes_util,
            "nodes_diff": nodes_diff,
            "total_util": total_util,
            "total_diff": total_diff,
            "pair_supported": pair_supported,
            "net_supported": net_supported,
        }

    remaining_edges = set(itertools.combinations(graph.nodes, 2)) - set(graph.edges)
    added_edges = {edge: new_edge_stat(edge) for edge in remaining_edges}
    exist_edges = {edge: exist_edge_stat(edge) for edge in graph.edges}
    added_edges_improve = {k: v for k, v in added_edges.items() if v["net_supported"]}
    added_edge_net_improve = None
    if added_edges_improve:
        added_edge_net_improve = max(
            added_edges_improve, key=lambda x: added_edges[x]["total_diff"]
        )

    return {
        "graph": graph,
        "current_util": current_util,
        "exist_edges": exist_edges,
        "added_edges": added_edges,
        "added_edge_net_improve": added_edge_net_improve,
    }


def calc_max_util(numb, delta, cost):
    if cost < delta * (1 - delta):
        return (numb - 1) * numb * (delta - cost)
    if cost < delta + (numb - 2) * delta * delta / 2:
        return 2 * (numb - 1) * (delta - cost) + (numb - 1) * (numb - 2) * delta * delta
    return 0


pos = {}


def description_card():
    """
    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card",
        children=[
            html.H5("Network formation"),
            html.H3("Symmetric Connection Model Demo"),
            html.Div(
                id="intro",
                children="Explore symmetric connection model calculations. Provide number of nodes, direct connection benefit (delta), connection cost and add/drop edges.",
            ),
        ],
    )


def generate_control_card():
    """
    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[
            html.P("Number of nodes"),
            dcc.Input(id="nodes", type="number", min=1, step=1, value=4),
            html.Br(),
            html.P("Benefit parameter"),
            dcc.Input(id="delta", type="number", min=0, max=1, step=0.1, value=0.5),
            html.Br(),
            html.P("Cost parameter"),
            dcc.Input(id="cost", type="number", min=0, max=1, step=0.01, value=0.5),
            html.Br(),
            html.P(id="maxutil", children="Max utility"),
            html.P("Color mode"),
            dcc.RadioItems(
                id="color",
                options=["Pairwise stable", "Efficient"],
                value="Pairwise stable",
                inline=True,
            ),
            html.Br(),
            html.Br(),
            html.P("Select edges"),
            dcc.Dropdown(
                id="edges-select",
                multi=True,
            ),
        ],
    )


def create_net_formation_app(app):
    app.layout = html.Div(
        id="app-container",
        style={"display": "flex"},
        children=[
            html.Div(
                id="left-column",
                style={"width": "30.6666666667%"},
                children=[description_card(), generate_control_card()]
                + [
                    html.Div(
                        ["initial child"],
                        id="output-clientside",
                        style={"display": "none"},
                    )
                ],
            ),
            # Right column
            html.Div(
                id="right-column",
                style={"width": "65.3333333333%"},
                children=[
                    html.Div(
                        id="patient_volume_card",
                        children=[
                            dcc.Graph(id="network"),
                        ],
                    ),
                    html.Div(
                        children=[
                            html.H5("Total utility"),
                            html.Div(id="totalutil", children=[]),
                            html.Br(),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.H5("Active links"),
                            html.Div(id="activelinks", children=[]),
                            html.Br(),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.H5("Possible links"),
                            html.P(id="newlinks", children="Possible links"),
                            html.Br(),
                        ]
                    ),
                ],
            ),
        ],
    )

    @app.callback(
        Output("edges-select", "options"),
        [
            Input("nodes", "value"),
        ],
    )
    def update_node_number(numb_nodes):
        graph = nx.empty_graph(numb_nodes)
        global pos
        pos = nx.spring_layout(graph)

        return [
            {"label": f"({x[0]}, {x[1]})", "value": f"{x[0]}, {x[1]}"}
            for x in itertools.combinations(graph.nodes, 2)
        ]

    @app.callback(
        Output("network", "figure"),
        [
            Input("nodes", "value"),
            Input("edges-select", "value"),
            Input("delta", "value"),
            Input("cost", "value"),
            Input("color", "value"),
        ],
    )
    def update_chart(numb_nodes, edges, delta, cost, color):
        graph = nx.empty_graph(numb_nodes)
        if edges:
            edges_list = [(int(y[0]), int(y[1])) for y in [x.split(",") for x in edges]]
            graph.add_edges_from(edges_list)
        graph_stat = analyze_network(graph, delta, cost)

        return plotly_network(
            graph_stat,
            pos,
            "pair_supported" if color == "Pairwise stable" else "net_supported",
        )

    @app.callback(
        [
            Output("activelinks", "children"),
            Output("newlinks", "children"),
            Output("totalutil", "children"),
            Output("maxutil", "children"),
        ],
        [
            Input("nodes", "value"),
            Input("edges-select", "value"),
            Input("delta", "value"),
            Input("cost", "value"),
        ],
    )
    def update_text(numb_nodes, edges, delta, cost):
        graph = nx.empty_graph(numb_nodes)
        if edges:
            edges_list = [(int(y[0]), int(y[1])) for y in [x.split(",") for x in edges]]
            graph.add_edges_from(edges_list)
        graph_stat = analyze_network(graph, delta, cost)
        active_links = html.Div(
            [
                html.P(
                    f"({x[0]}, {x[1]}) -> net utility diff = {graph_stat['exist_edges'][x]['total_diff']:.2f}, node {x[0]} diff = {graph_stat['exist_edges'][x]['nodes_diff'][x[0]]:.2f}, node {x[1]} diff  = {graph_stat['exist_edges'][x]['nodes_diff'][x[1]]:.2f}"
                )
                for x in graph_stat["exist_edges"]
            ]
        )

        new_links = html.Div(
            [
                html.P(
                    f"({x[0]}, {x[1]}) -> net utility diff = {graph_stat['added_edges'][x]['total_diff']:.2f}, node {x[0]} diff = {graph_stat['added_edges'][x]['nodes_diff'][x[0]]:.2f}, node {x[1]} diff  = {graph_stat['added_edges'][x]['nodes_diff'][x[1]]:.2f}"
                )
                for x in graph_stat["added_edges"]
            ]
        )

        total_util = f"{sum(calc_util(graph, delta, cost).values()):.2f}"

        maxutil = f"Max utility:  {calc_max_util(numb_nodes, delta, cost):.2f}"

        return active_links, new_links, total_util, maxutil


# Run the server
if __name__ == "__main__":
    app = dash.Dash(
        __name__,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"}
        ],
    )
    create_net_formation_app(app)
    app.run_server(debug=True)
