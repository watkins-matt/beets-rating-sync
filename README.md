# beets-rating-sync
beets-rating-sync allows you to synchronize your favorite songs from Last.fm and Musicbrainz with your Beets library.

All of your song ratings are stored as user collections in Musicbrainz which can be edited online. Song ratings are stored as flexible attributes in Beets, which means you can easily create smart playlists of certain song ratings using the `rating` flexible attribute.

After using this plugin, looking up all of your 5 star rated songs is as simple as `beet ls rating:5`

## Installation

This plugin requires the following packages:
- musicbrainzngs
- thefuzz


Install them with pip first:
```
$ pip install musicbrainzngs
$ pip install thefuzz
```

Now download beets-rating-sync to a folder and add the path to your config.yaml
```
pluginpath:
    - /path/to/beetsdir
```

Finally, add the plugin to your plugin list in config.yaml

```
plugins: [
    another_plugin_here,
    rating_sync,
    more_plugins_here
  ]
```
## Configuration
Configure it in config.yaml as follows:

```
rating_sync:
  mb_user: your_musicbrainz_username_here
  mb_pass: your_musicbrainz_password_here
  lastfm_user: your_lastfm_username_here
```

For it to sync correctly to Musicbrainz, you must manually create a collection for each star rating, named as follows:
- 1 Star
- 2 Star
- 3 Star
- 4 Star
- 5 Star

These are the default names that must be used; these will be user configurable in the future. Song ratings are stored and retrieved from these collections as a workaround for limitations in the Musicbrainz API which do not allow for the fetching of individual song ratings for a given user.

## Commands
```
$ beet ratingsync
```
This is the default, legacy sync method. This will first import all of your liked songs from Last.fm, then upload them as 4-star rated songs to your collections (you can increase or decrease the rating later on the Musicbrainz website). Note that if you have a lot of songs, this sync method can be slow due to Musicbrainz API rate limits. Finally, it will copy all of the song ratings to Beets using flexible attributes.

```
$ beet newratingsync
```
This is the in-development sync method which will eventually replace the legacy sync method. This method uses caching to make synchronizing nearly instant. It will eventually allow the cache to be refreshed manually or after a certain period of time. This method will also export all of your song ratings to csv for
easy backup and restore later.

## How To Change Ratings

### Adding New Ratings
Navigate to the recording you wish to rate on Musicbrainz and click the add to collection button on the sidebar.
For example, click the "Add to 5 Star" button to rate a song 5 stars.

### Removing A Rating
Navigate to the recording you wish to remove on Musicbrainz and click the remove from collection button on the sidebar.
For example, click the "Remove from 5 Star" button to remove a song from your 5 star list.

## License
Copyright (c) 2023 - Matthew Watkins

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
