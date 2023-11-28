import tmdbsimple as tmdb

tmdb.API_KEY = 'a535bcba0d8c195dde178e69478394ee'

discover = tmdb.Discover()
response = discover.movie(vote_average_gte=1, vote_average_lte=10, sort_by='vote_average.asc')

for s in discover.results:
    print(s['title'], s['vote_average'])

print('------------------')

response = discover.movie(vote_average_gte=7, vote_average_lte=10, sort_by='vote_average.desc')

for s in discover.results:
    print(s['title'], s['vote_average'])
