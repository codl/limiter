this is a thing that will limit your tweet count to whichever value you want, deleting random tweets when it goes over the limit

## usage

```
pip install -r requirements.txt
```

then put your twitter credentials in an environment file like

```
cat > credentials << EOF
CONSUMER_KEY=blabl
CONSUMER_SECRET=hjklhjklhklj
ACCESS_TOKEN=ahhhh
ACCESS_TOKEN_SECRET=btw get these by making an app at apps.twitter.com if you dont know
EOF
```

then in a crontab

```
cd /bla/bla/limiter; env $(cat credentials) python limiter.py update # to fetch new tweets
cd /bla/bla/limiter; env $(cat credentials) python limiter.py prune -t 500 # to delete tweets until you're at 500
```

also theres usage messages if you run it with `--help`

thanks dont blame me if you lose important tweets
