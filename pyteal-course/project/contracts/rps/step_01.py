from pyteal import *
from pyteal.ast.bytes import Bytes
from pyteal_helpers import program


def approval():
    local_opponent = Bytes("opponent") # byteslice
    local_wager = Bytes("wager") #uint64
    local_commitment = Bytes("commitment") # byteslice --> hashed play
    local_reveal = Bytes("reveal")  #byteslice --> unhashed play

    # operations
    op_challenge = Bytes("challenge")
    op_accept = Bytes("accept")
    op_reveal = Bytes("reveal")

    @Subroutine(TealType.none)
    def reset(account: Expr):
        return Seq(
            App.localPut(account, local_opponent, Bytes("")),
            App.localPut(account, local_wager, Int(0)),
            App.localPut(account, local_commitment, Bytes("")),
            App.localPut(account, local_reveal, Bytes(""))
        )

    @Subroutine(TealType.uint64)
    def is_empty(account: Expr):
        return Return(
            And(
                App.localGet(account, local_opponent) == Bytes(""),
                App.localGet(account, local_wager) == Bytes(""),
                App.localGet(account, local_commitment) == Bytes(""),
                App.localGet(account, local_reveal) == Bytes("")
            )
        )

    @Subroutine(TealType.none)
    def create_challenge():
        return Seq(
            program.check_self(
                group_size = Int(2),
                group_index = Int(0)
            ),
            program.check_rekey_zero(2),
            Assert(
                And(
                    # Check wager payment transaction: The second transaction
                    Gtxn[1].type_enum() == TxnType.Payment,
                    Gtxn[1].receiver() == Global.current_application_address(),
                    Gtxn[1].close_remainder_to() == Global.zero_address(),

                    # Check if opponent has opted in
                    App.optedIn(Txn.accounts[1], Global.current_application_id()),

                    # Check if both accounts are available to play
                    is_empty(Txn.sender()),
                    is_empty(Txn.accounts[1]),

                    # Check commitment: 2nd argument
                    Txn.application_args.length() == Int(2)
                ),
            ),

            App.localPut(Txn.sender(), local_opponent, Txn.accounts[1]),
            App.localPut(Txn.sender(), local_wager, Gtxn[1].amount()),
            App.localPut(Txn.sender(), local_commitment, Txn.application_args[1]),
            Approve()
        )

    @Subroutine(TealType.none)
    def accept_challenge():
        return Reject()

    @Subroutine(TealType.none)
    def reveal():
        return Reject()


    return program.event(
        init = Approve(),
        opt_in = Seq(
            reset(Int(0)),
            Approve()
        ),
        no_op = Seq(
            Cond(
                [Txn.application_args[0] == op_challenge, create_challenge()],
                [Txn.application_args[0] == op_accept, accept_challenge()],
                [Txn.application_args[0] == op_reveal, reveal()],
            ),
            Reject()
        )
    )


def clear():
    return Approve()


