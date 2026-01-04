import http.client

conn = http.client.HTTPSConnection("weatherapi230.p.rapidapi.com")

headers = {
    'x-rapidapi-key': "6722a263bfmsh1eda951848073d8p13e894jsnfce217ba7f2f",
    'x-rapidapi-host': "weatherapi230.p.rapidapi.com"
}

conn.request("GET", "/current?units=metric&location=Lon", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))