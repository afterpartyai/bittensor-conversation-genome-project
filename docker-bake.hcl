target "miner" {
  context = "."
  dockerfile = "Dockerfile"

  platforms = ["linux/amd64", "linux/arm64"]
  tags = [
    "readyai/bittensor-readyai-sn33:2.39.76",
  ]

  output = ["type=registry"]
}
