from django.urls import path
from . import views

app_name = "rewards"

urlpatterns = [
    
    # Fitur Hadiah
    path('hadiah/', views.hadiah_list, name='hadiah_list'),
    path('hadiah/create/', views.hadiah_create, name='hadiah_create'),
    path('hadiah/edit/<str:pk>/', views.hadiah_update, name='hadiah_update'),
    path('hadiah/delete/<str:pk>/', views.hadiah_delete, name='hadiah_delete'),
 
    # Fitur Mitra
    path('mitra/', views.mitra_list, name='mitra_list'),
    path('mitra/create/', views.mitra_create, name='mitra_create'),
    path('mitra/update/<str:email>/', views.mitra_update, name='mitra_update'),
    path('mitra/delete/<str:email>/', views.mitra_delete, name='mitra_delete'),
 
    path('katalog/', views.katalog, name='katalog'),
    path('beli_package/', views.beli_package, name='beli_package'),
    path('info_tier/', views.info_tier, name='info_tier'),
    path("laporan/", views.laporan_transaksi, name="laporan_transaksi"),

]