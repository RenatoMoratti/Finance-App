import secrets

def generate_secret_key(length_bytes: int = 32) -> str:
    """Gera uma chave hex segura para uso em FLASK_SECRET_KEY.

    length_bytes: número de bytes aleatórios. 32 -> 64 chars hex.
    """
    return secrets.token_hex(length_bytes)

if __name__ == "__main__":
    key = generate_secret_key()
    print("\nChave gerada (não reutilize em outros projetos):\n")
    print(key)
    print("\nComo usar:")
    print("1. Abra o arquivo .env")
    print("2. Defina/edite a linha: FLASK_SECRET_KEY=" + key)
    print("3. Salve e reinicie a aplicação")
    print("\nVocê pode ajustar o tamanho chamando: python generate_secret_key.py  (usa 32 bytes)")
