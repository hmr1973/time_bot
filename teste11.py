import pyotp

two_factor_seed = "BW64LFQ6L54HTGDKMED5E73J7HY46QVH"  # Substitua pela sua chave
try:
    totp = pyotp.TOTP(two_factor_seed)
    print("Código 2FA gerado:", totp.now())
except Exception as e:
    print("Erro ao gerar código 2FA:", e)