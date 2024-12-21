{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    rust-overlay.url = "github:oxalica/rust-overlay";
    rust-overlay.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    rust-overlay,
  } @ inputs:
    flake-utils.lib.eachDefaultSystem
    (
      system: let
        overlays = [(import rust-overlay)];
        pkgs = import nixpkgs {inherit system overlays;};

        rustPkg = pkgs.rust-bin.stable.latest.default;
        pythonPkg = pkgs.python3;
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [alejandra maturin pythonPkg rustPkg];

          shellHook = ''
            export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib.outPath}/lib:${pkgs.pythonManylinuxPackages.manylinux2014Package}/lib:$LD_LIBRARY_PATH";
            test -d .nix-venv || ${pythonPkg.interpreter} -m venv .nix-venv
            source .nix-venv/bin/activate
          '';
        };
      }
    );
}
