import streamlit_authenticator as stauth
import yaml

print(f"Stauth version: {getattr(stauth, '__version__', 'unknown')}")

mock_config = {
    'credentials': {'usernames': {}}, 
    'cookie': {'name': 'test', 'key': 'test', 'expiry_days': 1}
}

try:
    auth = stauth.Authenticate(
        credentials=mock_config['credentials'],
        cookie_name='test',
        cookie_key='test',
        cookie_expiry_days=1
    )
    
    print("\nInstance dir:")
    print(dir(auth))
    
    print("\nInstance vars:")
    print(vars(auth).keys())

except Exception as e:
    print(f"Error instantiating: {e}")
