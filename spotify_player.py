import os
from typing import Optional, Dict, Any

class SpotifyPlayer:
    def __init__(self):
        self.spotify_available = False
        self.spotify = None
        
        # Only try to import if credentials are set
        if os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET"):
            try:
                import spotipy
                from spotipy.oauth2 import SpotifyClientCredentials
                
                auth_manager = SpotifyClientCredentials()
                self.spotify = spotipy.Spotify(auth_manager=auth_manager)
                self.spotify_available = True
                print("✅ Spotify initialized successfully")
            except (ImportError, Exception) as e:
                print(f"⚠️ Spotify not available - music features disabled: {str(e)}")

    def get_workout_playlist(self, workout_type: str = "cardio") -> Optional[Dict[str, Any]]:
        """Get a workout playlist based on the type of workout"""
        if not self.spotify_available:
            return None

        try:
            # Default playlists for different workout types
            playlist_keywords = {
                "cardio": "cardio workout",
                "strength": "gym workout",
                "yoga": "yoga flow",
                "hiit": "hiit workout",
                "general": "workout motivation"
            }
            
            # Search for a playlist
            keyword = playlist_keywords.get(workout_type, playlist_keywords["general"])
            results = self.spotify.search(q=keyword, type="playlist", limit=1)
            
            if results and results["playlists"]["items"]:
                playlist = results["playlists"]["items"][0]
                return {
                    "name": playlist["name"],
                    "url": playlist["external_urls"]["spotify"],
                    "uri": playlist["uri"]
                }
            return None
            
        except Exception as e:
            print(f"Error getting workout playlist: {e}")
            return None

    def get_playlist_embed(self, playlist_uri: str) -> Optional[str]:
        """Generate an embed code for a Spotify playlist"""
        if not self.spotify_available or not playlist_uri:
            return None
            
        try:
            # Convert URI to embed format
            playlist_id = playlist_uri.split(":")[-1]
            embed_html = f'<iframe src="https://open.spotify.com/embed/playlist/{playlist_id}" width="300" height="380" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>'
            return embed_html
        except Exception as e:
            print(f"Error generating playlist embed: {e}")
            return None
