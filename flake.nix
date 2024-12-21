{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

    rust-overlay.url = "github:oxalica/rust-overlay";
    rust-overlay.inputs.nixpkgs.follows = "nixpkgs";

    pyproject-nix.url = "github:pyproject-nix/pyproject.nix";
    pyproject-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    rust-overlay,
    pyproject-nix,
  } @ inputs:
    flake-utils.lib.eachDefaultSystem
    (
      system: let
        overlays = [(import rust-overlay)];
        pkgs = import nixpkgs {inherit system overlays;};

        project = pyproject-nix.lib.project.loadPyproject {
          projectRoot = ./.;
        };

        rust = pkgs.rust-bin.stable.latest.default;
        python = pkgs.python3.override {
          self = python;
          packageOverrides = pyfinal: pyprev: {
            inherit (pkgs) maturin;
            typer-slim = pyfinal.typer;
          };
        };
      in {
        devShells.default = let
          pythonEnv = python;
          /*
                              assert project.validators.validateVersionConstraints {inherit python;} == {};
          python.withPackages (project.renderers.withPackages {inherit python;});
          */
        in
          pkgs.mkShell {
            buildInputs = with pkgs; [alejandra maturin rust pythonEnv];

            shellHook = ''
              export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib.outPath}/lib:${pkgs.pythonManylinuxPackages.manylinux2014Package}/lib:$LD_LIBRARY_PATH";
              test -d .nix-venv || ${python.interpreter} -m venv .nix-venv
              source .nix-venv/bin/activate
            '';
          };

        packages.default = let
          # Returns an attribute set that can be passed to `buildPythonPackage`.
          attrs = project.renderers.buildPythonPackage {
            inherit python;
          };
        in
          # Pass attributes to buildPythonPackage.
          # Here is a good spot to add on any missing or custom attributes.
          python.pkgs.buildPythonPackage attrs;
      }
    );
}
