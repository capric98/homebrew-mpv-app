cask "mpv-app" do
  version "0.42.0"

  on_arm do
    sha256 "be1b8d2445e6880860869c080b8710dee189721f1fa4689840db6a2c10d7be69"
    url "https://github.com/mpv-player/mpv/releases/download/v#{version}/mpv-v#{version}-macos-15-arm.zip"
    depends_on macos: :sequoia
  end

  on_intel do
    sha256 "2d2f34350ff844b6014c35f21ca142937275e19c0c673150a8564fcd2f3bfa14"
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
