import time, json, threading
from datetime import datetime
from pocketoptionapi.stable_api import PocketOption
import pocketoptionapi.global_value as global_value

# Configuración de logging para mantener la salida limpia
global_value.loglevel = 'WARNING'

# --- 1. REEMPLAZA ESTE SSID POR UNO NUEVO Y FUNCIONAL ---
# El que está aquí ya ha expirado y causará un error.
ssid = '42["auth",{"session":"gqep422ie95ar8uabq0q9nsdsf","isDemo":1,"uid":107695044,"platform":2,"isFastHistory":true,"isOptimized":true}]'
demo = True

# Se inicializa la API con tus datos
api = PocketOption(ssid, demo)


def get_and_print_binary_assets():
    """
    Esta función procesa la información de activos recibida de la API
    y muestra en pantalla todos los que están disponibles para operar en binarias.
    """
    print("\n" + "="*60)
    print("   ✅ LISTA DE ACTIVOS BINARIOS DISPONIBLES PARA OPERAR")
    print("="*60)
    
    try:
        # La librería guarda los datos de los activos en esta variable global
        asset_data_json = global_value.PayoutData
        if asset_data_json is None:
            print("No se recibieron datos de los activos.")
            return False

        asset_data = json.loads(asset_data_json)
        found_assets = 0
        
        for asset_list in asset_data:
            # Según la estructura de datos, el índice 14 es el que nos dice si un activo está 'activo' (True/False)
            is_active_for_binary = asset_list[14]
            
            # Si el activo está disponible para binarias, lo mostramos
            if is_active_for_binary:
                asset_name = asset_list[1]  # Este es el nombre que necesitas para operar (ej: 'EUR/USD' o '#AAPL_otc')
                asset_type = asset_list[3]  # El tipo de activo (ej: 'currency', 'stock')
                payout = asset_list[5]      # El porcentaje de payout
                
                print(f"  - Nombre: {asset_name}  (Tipo: {asset_type}, Payout: {payout}%)")
                found_assets += 1
        
        if found_assets == 0:
            print("No se encontraron activos binarios abiertos en este momento.")
        
        print("="*60)
        return True
    except Exception as e:
        print(f"❌ Error al procesar la lista de activos: {e}")
        return False


# --- Bloque de ejecución principal ---
if __name__ == "__main__":
    print("🚀 Conectando a PocketOption para obtener la lista de activos...")
    
    # Nos conectamos a la API
    api.connect()

    # Esperamos de forma segura hasta que la variable PayoutData sea llenada por la API
    print("Esperando recibir datos de los activos del servidor...")
    timeout = 30  # Esperar un máximo de 30 segundos
    start_time = time.time()
    while global_value.PayoutData is None and time.time() - start_time < timeout:
        time.sleep(1)
    
    if global_value.PayoutData is None:
        print("❌ Error: No se recibieron los datos de los activos después de 30 segundos. El SSID podría ser inválido.")
    else:
        print("Datos recibidos. Mostrando la lista...")
        get_and_print_binary_assets()
    
    print("\n🔌 Proceso completado. Puedes usar los nombres de la lista en tu bot principal.")
    # El script terminará aquí automáticamente
    
