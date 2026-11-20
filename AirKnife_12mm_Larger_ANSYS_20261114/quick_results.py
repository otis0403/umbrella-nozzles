from post_results import residuals,metrics
residuals()
body,jets=metrics(plots=False)
print('BODY_COMPARISON',body,flush=True)
