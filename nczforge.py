"""
nczforge.py - NCZ Forge Entry Point
Netcad NCZ & CAD Çevirici ve Vektör PDF / Yüksek Çözünürlüklü TIF Dışa Aktarıcı
"""
import multiprocessing

if __name__ == "__main__":
    # Paketlenmiş exe'de paralel toplu dönüştürmenin alt süreçleri için gerekli
    multiprocessing.freeze_support()
    from dxftoncz_gui import main

    main()
