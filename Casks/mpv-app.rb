cask "mpv-app" do
  version "0.41.0"

  on_arm do
    sha256 "5c96f9b21355fc0a11d2e2161ad65f33031070e9fb3f6bd9865fb459b94587e6"
    url "https://github.com/mpv-player/mpv/releases/download/v#{version}/mpv-v#{version}-macos-14-arm.zip"
    depends_on macos: :sonoma
  end

  on_intel do
    sha256 "41003617ab4f7784394b5ddea7ce51b3e0838e8cfc8166ad1a378b2eda3b583c"
    url "https://github.com/mpv-player/mpv/releases/download/v#{version}/mpv-v#{version}-macos-15-intel.zip"
    depends_on macos: :sequoia
  end

  name "mpv"
  desc "Media player distributed as a complete macOS app"
  homepage "https://mpv.io/"

  livecheck do
    url "https://github.com/mpv-player/mpv"
    strategy :github_latest
  end

  conflicts_with cask: ["mpv-macwrapper", "mpv-official", "stolendata-mpv"]

  container nested: "mpv.tar.gz"
  app "mpv.app"

  caveats <<~EOS
    This is a community-maintained tap using builds from mpv-player/mpv.
    The mpv formula is not required. Gatekeeper checks remain enabled.
  EOS
end
