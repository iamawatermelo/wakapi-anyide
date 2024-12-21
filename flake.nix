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

        python = pkgs.python3;
        rust = pkgs.rust-bin.stable.latest.default;
        rustPlatform = pkgs.makeRustPlatform {
          rustc = rust;
          cargo = rust;
        };
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [alejandra maturin rust python];

          shellHook = ''
            export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib.outPath}/lib:${pkgs.pythonManylinuxPackages.manylinux2014Package}/lib:$LD_LIBRARY_PATH";
            test -d .nix-venv || ${python.interpreter} -m venv .nix-venv
            source .nix-venv/bin/activate
          '';
        };

        packages.default = python.pkgs.buildPythonApplication rec {
          name = "wakapi-anyide-${version}";
          version = "0.6.8";
          pyproject = true;

          cargoDeps = rustPlatform.fetchCargoTarball {
            inherit src;
            hash = "sha256-qSU1QkYeGrVqWo+H+nB0DziJTjagaPczQhONV6ZFX14=";
          };

          nativeBuildInputs = with pkgs; [
            maturin
            rustPlatform.cargoSetupHook
            rustPlatform.maturinBuildHook
          ];

          src = ./.;
        };
      }
    );
}
