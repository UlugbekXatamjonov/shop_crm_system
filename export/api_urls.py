"""
============================================================
EXPORT APP — URL'lar
============================================================
Prefix: /api/v1/export/

EXPORT (yuklab olish):
  GET /api/v1/export/sales/                  ?format=excel|pdf &date_from &date_to &branch &smena &status
  GET /api/v1/export/expenses/               ?format=excel|pdf &date_from &date_to &branch &smena &category
  GET /api/v1/export/stocks/                 ?branch &warehouse
  GET /api/v1/export/stock-movements/        ?format=excel|pdf &date_from &date_to &branch &warehouse &movement_type
  GET /api/v1/export/suppliers/              ?format=excel|pdf &status

IMPORT (shablon + yuklash):
  GET  /api/v1/export/products/template/         → bo'sh .xlsx
  POST /api/v1/export/products/import/           → {created, skipped, errors}
  GET  /api/v1/export/customers/template/
  POST /api/v1/export/customers/import/
  GET  /api/v1/export/stock-movements/template/
  POST /api/v1/export/stock-movements/import/
  GET  /api/v1/export/suppliers/template/
  POST /api/v1/export/suppliers/import/
  GET  /api/v1/export/subcategories/template/
  POST /api/v1/export/subcategories/import/
"""

from django.urls import path

from .views import (
    CustomerImportView,
    ExpenseExportView,
    ProductImportView,
    StockExportView,
    StockMovementExportView,
    StockMovementImportView,
    SubCategoryImportView,
    SupplierExportView,
    SupplierImportView,
    SaleExportView,
)

urlpatterns = [
    # ---- EXPORT ----
    path('sales/',                 SaleExportView.as_view(),          name='export-sales'),
    path('expenses/',              ExpenseExportView.as_view(),        name='export-expenses'),
    path('stocks/',                StockExportView.as_view(),          name='export-stocks'),
    path('stock-movements/',       StockMovementExportView.as_view(),  name='export-stock-movements'),
    path('suppliers/',             SupplierExportView.as_view(),       name='export-suppliers'),

    # ---- IMPORT — Mahsulot ----
    path('products/template/',     ProductImportView.as_view(),        name='import-products-template'),
    path('products/import/',       ProductImportView.as_view(),        name='import-products'),

    # ---- IMPORT — Mijoz ----
    path('customers/template/',    CustomerImportView.as_view(),       name='import-customers-template'),
    path('customers/import/',      CustomerImportView.as_view(),       name='import-customers'),

    # ---- IMPORT — StockMovement ----
    path('stock-movements/template/', StockMovementImportView.as_view(), name='import-movements-template'),
    path('stock-movements/import/',   StockMovementImportView.as_view(), name='import-movements'),

    # ---- IMPORT — Yetkazib beruvchi ----
    path('suppliers/template/',    SupplierImportView.as_view(),       name='import-suppliers-template'),
    path('suppliers/import/',      SupplierImportView.as_view(),       name='import-suppliers'),

    # ---- IMPORT — SubKategoriya ----
    path('subcategories/template/', SubCategoryImportView.as_view(),   name='import-subcategories-template'),
    path('subcategories/import/',   SubCategoryImportView.as_view(),   name='import-subcategories'),
]
