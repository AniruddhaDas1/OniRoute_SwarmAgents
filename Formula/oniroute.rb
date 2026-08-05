# OniRoute Homebrew Formula
# Install: brew install oniroute/tap/oniroute
# Usage:   oniroute build "a real estate website"

class Oniroute < Formula
  desc "Organization Level Swarm Coding AI Agents"
  homepage "https://github.com/AniruddhaDas1/OniRoute_SwarmAgents"
  url "https://github.com/AniruddhaDas1/OniRoute_SwarmAgents/archive/refs/tags/v1.2.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "Apache-2.0"
  head "https://github.com/AniruddhaDas1/OniRoute_SwarmAgents.git", branch: "main"

  depends_on "python@3.14"
  depends_on "git"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "OniRoute", shell_output("#{bin}/oniroute --help")
  end
end
