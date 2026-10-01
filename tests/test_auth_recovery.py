from unittest.mock import MagicMock

import pytest
from spotipy.exceptions import SpotifyOauthError

from dj_rara.spotify_auth import SpotifyAuthenticator


@pytest.fixture
def oauth(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('SPOTIFY_CLIENT_ID', 'test-id')
    monkeypatch.setenv('SPOTIFY_CLIENT_SECRET', 'test-secret')
    monkeypatch.setattr('dj_rara.spotify_auth.load_dotenv', lambda: None)
    manager = MagicMock()
    monkeypatch.setattr('dj_rara.spotify_auth.SpotifyOAuth', lambda **kwargs: manager)
    monkeypatch.setattr('dj_rara.spotify_auth.spotipy.Spotify', MagicMock())
    return manager


def test_revoked_token_reauthorizes_once(oauth, tmp_path, capsys):
    cache = tmp_path / '.cache'
    cache.write_text('old-token')
    env = tmp_path / '.env'
    env.write_text('credentials-preserved')
    oauth.get_access_token.side_effect = [
        SpotifyOauthError('revoked', error='invalid_grant'), 'fresh-token',
    ]
    SpotifyAuthenticator().authenticate()
    assert oauth.get_access_token.call_count == 2
    assert not cache.exists()
    assert env.read_text() == 'credentials-preserved'
    assert 'Please sign in again' in capsys.readouterr().err


def test_success_validates_before_returning(oauth):
    SpotifyAuthenticator().authenticate()
    oauth.get_access_token.assert_called_once_with(as_dict=False)


@pytest.mark.parametrize('error_code', ['invalid_client', 'temporarily_unavailable'])
def test_other_oauth_errors_preserve_cache(oauth, tmp_path, error_code):
    cache = tmp_path / '.cache'
    cache.write_text('keep-token')
    oauth.get_access_token.side_effect = SpotifyOauthError('failed', error=error_code)
    with pytest.raises(SpotifyOauthError):
        SpotifyAuthenticator().authenticate()
    assert cache.read_text() == 'keep-token'
    oauth.get_access_token.assert_called_once()


def test_reauthorization_failure_does_not_loop(oauth, tmp_path):
    (tmp_path / '.cache').write_text('old-token')
    oauth.get_access_token.side_effect = SpotifyOauthError('revoked', error='invalid_grant')
    with pytest.raises(SpotifyOauthError):
        SpotifyAuthenticator().authenticate()
    assert oauth.get_access_token.call_count == 2


def test_no_cache_does_not_retry_invalid_authorization_code(oauth):
    oauth.get_access_token.side_effect = SpotifyOauthError('bad code', error='invalid_grant')
    with pytest.raises(SpotifyOauthError):
        SpotifyAuthenticator().authenticate()
    oauth.get_access_token.assert_called_once()


def test_startup_handles_failure_on_first_profile_request(monkeypatch, capsys):
    from dj_rara.main import main
    monkeypatch.setenv('SPOTIFY_CLIENT_ID', 'test-id')
    monkeypatch.setenv('SPOTIFY_CLIENT_SECRET', 'test-secret')
    monkeypatch.setattr(SpotifyAuthenticator, 'authenticate', lambda self: MagicMock())
    constructor = MagicMock(side_effect=RuntimeError('profile unavailable'))
    monkeypatch.setattr('dj_rara.spotify_client.SpotifyClient', constructor)
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert 'authentication failed: profile unavailable' in capsys.readouterr().out
