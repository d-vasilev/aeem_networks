import itertools
import numbers
import dash
from dash import dcc, html, ctx
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
                color="#000000",
            ),
            hoverinfo="none",
            mode="lines",
        )

    edge_traces = [create_edge(edge) for edge in graph.edges()]

    node_x = []
    node_y = []
    node_color = []
    node_text = []
    node_util = []
    for node in graph_stat["current_util"]:  # graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_color.append(
            "#00ff00" if graph_stat["current_util"][node] >= 0 else "#ff0000"
        )
        node_text.append(node)
        node_util.append(graph_stat["current_util"][node])

    node_trace = go.Scatter(
        name="",
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textfont=dict(family="sans serif", size=24, color="Black"),
        # hoverinfo='text',
        customdata=node_util,
        hovertemplate="utility:%{customdata:.2f}",
        marker=dict(
            # showscale=True,
            # colorscale options
            #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
            #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
            #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
            # colorscale="Blues",
            # reversescale=True,
            color=node_color,
            size=40,
            # colorbar=dict(
            #     thickness=15,
            #     title="Node utility",
            #     xanchor="left",
            #     titleside="right",
            # ),
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


def analyze_network(graph, delta, cost, value, prob):
    benefit_1 = delta * prob * (value - cost) / (1 - delta)
    current_util = {
        node: degree * benefit_1 - cost * (degree > 0)
        for node, degree in dict(nx.degree(graph)).items()
    }

    return {
        "graph": graph,
        "current_util": current_util,
    }


pos = {}


def description_card():
    """
    :return: A Div containing dashboard title & descriptions.
    """
    return html.Div(
        id="description-card",
        children=[
            html.H5("Network Games"),
            html.H3("Repeated Games Demo"),
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

    graph = nx.empty_graph(7)
    global pos
    pos = nx.spring_layout(graph, seed=42)
    return html.Div(
        id="control-card",
        children=[
            html.P("Probability for favor"),
            dcc.Input(id="prob", type="number", min=0, max=1, step=0.1, value=0.1),
            html.Br(),
            html.P("Favor's value"),
            dcc.Input(id="value", type="number", min=0, max=1, step=0.01, value=0.9),
            html.Br(),
            html.P("Favor's cost"),
            dcc.Input(id="cost", type="number", min=0, max=1, step=0.01, value=0.5),
            html.Br(),
            html.P("Discount factor"),
            dcc.Input(id="delta", type="number", min=0, max=1, step=0.01, value=0.9),
            html.Br(),
            html.P("Predefined networks"),
            html.Button("Net1", id="button-net1", n_clicks=0),
            html.Button("Net2", id="button-net2", n_clicks=0),
            html.Br(),
            html.P("Select edges"),
            dcc.Dropdown(
                id="edges-select",
                options=[
                    {"label": f"({x[0]}, {x[1]})", "value": f"{x[0]}, {x[1]}"}
                    for x in itertools.combinations(range(7), 2)
                ],
                multi=True,
            ),
        ],
    )


def create_net_games_repeat_app(app):
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
                        children=[
                            dcc.Graph(id="network"),
                        ],
                    ),
                ],
            ),
        ],
    )

    @app.callback(
        Output("network", "figure"),
        [
            Input("edges-select", "value"),
            Input("delta", "value"),
            Input("cost", "value"),
            Input("value", "value"),
            Input("prob", "value"),
        ],
    )
    def update_chart(edges, delta, cost, value, prob):
        graph = nx.empty_graph(7)
        if edges:
            edges_list = [(int(y[0]), int(y[1])) for y in [x.split(",") for x in edges]]
            graph.add_edges_from(edges_list)
        graph_stat = analyze_network(graph, delta, cost, value, prob)

        return plotly_network(graph_stat, pos)

    @app.callback(
        Output("edges-select", "value"),
        [
            Input("button-net1", "n_clicks"),
            Input("button-net2", "n_clicks"),
        ],
    )
    def update_network(btn1, btn2):
        ctx_id = ctx.triggered_id
        if ctx_id == "button-net1":
            return [
                "0, 5",
                "3, 5",
                "2, 3",
                "2, 6",
                "1, 6",
                "1, 4",
                "0, 4",
            ]
        if ctx_id == "button-net2":
            return [
                "0, 5",
                "2, 3",
                "2, 6",
                "1, 6",
                "1, 4",
                "0, 4",
                "4, 6",
                "3, 6",
                "4, 5",
            ]
        return []


# Run the server
if __name__ == "__main__":
    app = dash.Dash(
        __name__,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"}
        ],
    )
    create_net_games_repeat_app(app)
    app.run_server(debug=True)
