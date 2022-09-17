#!/usr/bin/env python
# coding: utf-8

# In[1]:


from apiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow


# In[5]:


scopes = ['https://www.googleapis.com/auth/calendar']


# In[7]:


flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes=scopes)


# In[8]:


credentials = flow.run_console()


# In[ ]:


import pickle


# In[ ]:


pickle.dump(credentials, open("token.pkl", "wb"))

