target "miner_arm" {
  context = "."
  dockerfile = "Dockerfile"

  platforms = ["linux/arm64"]
  tags = [
    "readyai/bittensor-readyai-sn33:arm64-2.10.0",
  ]

  push = true
}

target "miner_x86" {
  context = "."
  dockerfile = "Dockerfile"

  platforms = ["linux/amd64"]
  tags = [
    "readyai/bittensor-readyai-sn33:amd64-2.10.0",
  ]
  
  push = true
}