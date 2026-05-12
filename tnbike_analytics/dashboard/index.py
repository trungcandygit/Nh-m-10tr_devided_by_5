"""Entry point — multi-page routing"""
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output

from app import app, server
import pages.p1_overview as p1
import pages.p2_product  as p2
import pages.p3_dealer   as p3
import pages.p4_geo      as p4
import pages.p5_forecast as p5
import pages.p6_ops      as p6

NAV_ITEMS = [
    ("/",          "Tổng quan"),
    ("/product",   "Sản phẩm"),
    ("/dealer",    "Đại lý"),
    ("/geo",       "Địa lý"),
    ("/forecast",  "Dự báo"),
    ("/ops",       "Vận hành"),
]

navbar = dbc.Navbar(
    dbc.Container([
        dbc.NavbarBrand("🚲 Xe đạp Thống Nhất", className="navbar-brand"),
        dbc.Nav([
            dbc.NavItem(dbc.NavLink(label, href=path, active="exact"))
            for path, label in NAV_ITEMS
        ], navbar=True, className="ms-auto"),
    ], fluid=True),
    color="dark", dark=True, className="mb-0",
    style={"fontFamily": "Segoe UI, sans-serif"},
)

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    navbar,
    html.Div(id="page-content"),
])


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname in ("/", "/overview"):  return p1.layout()
    if pathname == "/product":          return p2.layout()
    if pathname == "/dealer":           return p3.layout()
    if pathname == "/geo":              return p4.layout()
    if pathname == "/forecast":         return p5.layout()
    if pathname == "/ops":              return p6.layout()
    return p1.layout()


if __name__ == "__main__":
    app.run(debug=True, port=8050)